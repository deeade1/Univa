
class DispatchBatchPayload(graphene.ObjectType):
    assignments = graphene.List(DispatchAssignmentType)
    summary = graphene.JSONString()
    health = graphene.Field(DispatchHealthType)
    success = graphene.Boolean()
    total_processed = graphene.Int()
    successful_assignments = graphene.Int()
    failed_assignments = graphene.Int()


class DispatchSingleRequest(relay.ClientIDMutation):
    class Input:
        request_id = graphene.ID(required=True)
        force_mode = graphene.String()
        bypass_health_check = graphene.Boolean(default_value=False)

    assignment = graphene.Field(DispatchAssignmentType)
    health = graphene.Field(DispatchHealthType)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from transport.models.core.service_request import ServiceRequest
        from django.shortcuts import get_object_or_404
        from transport.services.dispatch.helpers import get_dispatch_health

        request = get_object_or_404(ServiceRequest, pk=input["request_id"])

        if request.provider_id:
            raise GraphQLError(f"Request {request.id} already assigned!")

        dispatcher, mode_used = resolve_dispatcher(
            force_mode=input.get("force_mode"),
            fallback=True,
            bypass_health=input.get("bypass_health_check"),
        )

        provider = dispatcher.dispatch_request(request)
        details = getattr(dispatcher, "last_assignment_details", {})

        match_score = details.get("match_score", 0.5)
        estimated_eta = details.get("estimated_eta", 15.0)

        # 🔥 broadcast real-time event
        broadcast_dispatch_event(
            request,
            provider,
            {"match_score": match_score, "estimated_eta": estimated_eta},
            mode_used,
        )

        assignment = DispatchAssignmentType(
            request_id=str(request.id),
            provider_id=str(provider.id) if provider else None,
            match_score=match_score,
            estimated_eta=estimated_eta,
            success=bool(provider),
            error=None if provider else "No provider found",
            mode_used=mode_used,
            timestamp=timezone.now(),
        )

        msg = (
            f"Dispatched request {request.id} to provider {provider.id}"
            if provider else f"No provider found for request {request.id}"
        )

        health = DispatchHealthType(
            **build_health_payload(get_dispatch_health(), mode_used)
        )

        return cls(
            assignment=assignment,
            health=health,
            success=bool(provider),
            message=msg,
        )


class DispatchBatch(relay.ClientIDMutation):
    """Dispatch multiple requests in batch"""
    assignments = graphene.List(DispatchAssignmentType)
    summary = graphene.JSONString()
    health = graphene.Field(DispatchHealthType)
    success = graphene.Boolean()
    total_processed = graphene.Int()
    successful_assignments = graphene.Int()
    failed_assignments = graphene.Int()

    class Input:
        request_ids = graphene.List(graphene.ID, required=True)
        batch_size = graphene.Int(default_value=50)
        force_mode = graphene.String()
        enable_fallback = graphene.Boolean(default_value=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            from transport.models.core.service_request import ServiceRequest
            from transport.services.dispatch.helpers import get_dispatch_health

            request_ids = [str(r) for r in input["request_ids"]]
            requests = ServiceRequest.objects.filter(
                id__in=request_ids,
                provider__isnull=True
            )

            if not requests.exists():
                raise GraphQLError("No valid unassigned requests found")

            if len(request_ids) > input["batch_size"]:
                raise GraphQLError("Batch size exceeded")

            dispatcher, mode_used = resolve_dispatcher(
                force_mode=input.get("force_mode"),
                fallback=input["enable_fallback"],
            )

            assignments = []

            # Async batch if supported
            if hasattr(dispatcher, "process_dispatch_batch"):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(dispatcher.process_dispatch_batch(list(requests)))

                    for r in results:
                        assignments.append(
                            DispatchAssignmentType(
                                request_id=str(r.request_id),
                                provider_id=str(r.provider_id),
                                match_score=getattr(r, "match_score", 0.5),
                                estimated_eta=getattr(r, "estimated_eta", 15.0),
                                success=True,
                                mode_used=mode_used,
                                timestamp=timezone.now()
                            )
                        )
                except Exception as e:
                    logger.error(f"Async batch fail: {e}")

            # Fallback sequential
            if not assignments:
                for req in requests:
                    try:
                        provider = dispatcher.dispatch_request(req)
                        assignments.append(
                            DispatchAssignmentType(
                                request_id=str(req.id),
                                provider_id=str(provider.id) if provider else None,
                                match_score=0.5,
                                estimated_eta=15.0,
                                success=bool(provider),
                                error=None if provider else "No provider found",
                                mode_used=mode_used,
                                timestamp=timezone.now(),
                            )
                        )
                    except Exception as e:
                        assignments.append(
                            DispatchAssignmentType(
                                request_id=str(req.id),
                                provider_id=None,
                                match_score=0.0,
                                estimated_eta=0.0,
                                success=False,
                                error=str(e),
                                mode_used=mode_used,
                                timestamp=timezone.now(),
                            )
                        )

            successful = sum(1 for a in assignments if a.success)
            failed = len(assignments) - successful

            summary = {
                "total": len(request_ids),
                "processed": len(assignments),
                "successful": successful,
                "failed": failed,
                "success_rate": (successful / len(assignments)) * 100 if assignments else 0,
                "mode_used": mode_used,
            }

            health = DispatchHealthType(**build_health_payload(get_dispatch_health(), mode_used))
            
            # Broadcast events (add your broadcast_dispatch_event function call here)
            # broadcast_dispatch_event(...)

            return cls(
                assignments=assignments,
                summary=summary,
                health=health,
                success=(failed == 0),
                total_processed=len(assignments),
                successful_assignments=successful,
                failed_assignments=failed,
            )

        except Exception as e:
            logger.error(f"Batch dispatch failed: {e}")
            raise GraphQLError(str(e))


class CheckDispatchHealth(relay.ClientIDMutation):
    class Input:
        detailed = graphene.Boolean(default_value=False)

    status = graphene.Field(DispatchHealthType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, detailed=False):
        try:
            from transport.services.dispatch.helpers import get_dispatch_health, get_dispatcher

            health_status = get_dispatch_health()
            dispatcher = get_dispatcher()
            mode_name = type(dispatcher).__name__.replace("DispatchService", "simple")
            mode_name = mode_name.replace("EnhancedUnifiedDispatcher", "enhanced")
            mode_name = mode_name.replace("AIDispatchOptimizer", "ai_optimizer")

            return cls(
                status=DispatchHealthType(
                    **build_health_payload(health_status, mode_name)
                )
            )
        except Exception as e:
            raise GraphQLError(str(e))

class SwitchDispatchMode(relay.ClientIDMutation):
    class Input:
        mode = graphene.String(required=True)
        duration_minutes = graphene.Int()

    status = graphene.Field(DispatchHealthType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, mode, duration_minutes=None):
        if not info.context.user.is_staff:
            raise GraphQLError("Admin only")

        valid = ["simple", "ai_optimizer", "enhanced", "auto"]
        if mode not in valid:
            raise GraphQLError(f"Mode must be one of: {', '.join(valid)}")

        try:
            from django.core.cache import cache
            from transport.services.dispatch.helpers import get_dispatch_health

            key = "dispatch_mode_override"
            ttl = (duration_minutes or 1440) * 60
            cache.set(key, mode, ttl)

            health = get_dispatch_health()

            return cls(
                status=DispatchHealthType(
                    **build_health_payload(health, mode)
                )
            )

        except Exception as e:
            raise GraphQLError(str(e))



class TransportMutation(graphene.ObjectType):
    
    
    dispatch_single_request = DispatchSingleRequest.Field()
    dispatch_batch = DispatchBatch.Field()
    check_dispatch_health = CheckDispatchHealth.Field()
    switch_dispatch_mode = SwitchDispatchMode.Field()

