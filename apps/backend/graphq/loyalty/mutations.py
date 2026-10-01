import graphene
from graphene import relay
from aacounts.models.profile import UserProfile

class UpdateLoyaltyPoints(relay.ClientIDMutation):
    class Input:
        delta = graphene.Int(required=True)

    success = graphene.Boolean()
    new_points = graphene.Int()

    @login_required
    @classmethod
    def mutate_and_get_payload(self, info, delta):
        user = info.context.user
        profile = UserProfile.objects.get(user=user)

        profile.loyalty_points = max(profile.loyalty_points + delta, 0)
        profile.save()

        return UpdateLoyaltyPoints(success=True, new_points=profile.loyalty_points)

class RedeemLoyaltyReward(relay.ClientIDMutation):
    class Input:
        reward_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    remaining_points = graphene.Int()

    @login_required
    @classmethod
    def mutate_and_get_payload(self, info, reward_id):
        user = info.context.user
        profile = UserProfile.objects.get(user=user)

        try:
            reward = LoyaltyRewardTier.objects.get(id=reward_id, active=True)
        except LoyaltyRewardTier.DoesNotExist:
            raise GraphQLError("Reward not found or inactive.")

        if profile.loyalty_points < reward.points_needed:
            raise GraphQLError("Not enough loyalty points to redeem this reward.")

        # Deduct points
        profile.loyalty_points -= reward.points_needed
        profile.save()

        # Log redemption
        LoyaltyHistory.objects.create(
            user=user,
            reward=reward.reward,
            date_redeemed=timezone.now()
        )

        return RedeemLoyaltyReward(
            success=True,
            message=f"Successfully redeemed: {reward.reward}",
            remaining_points=profile.loyalty_points
        )


# Loyalty & Notifications
    update_loyalty_points = UpdateLoyaltyPoints.Field()
    redeem_loyalty_reward = RedeemLoyaltyReward.Field()