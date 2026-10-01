# =====================
# TRANSACTION SERVICE LAYER
# =====================
class TransactionService:
    """
    ✅ Service layer for transaction operations.
    This encapsulates business logic and should be used by GraphQL mutations.
    """
    
    @staticmethod
    def create_transaction(property, buyer, seller, offer_price, **kwargs):
        """Create a new transaction with validation"""
        # ✅ Check if transaction can be created
        can_create, message = Transaction.can_create_transaction(property, buyer, seller)
        if not can_create:
            raise ValidationError(message)
        
        # Create the transaction
        transaction = Transaction.objects.create(
            property=property,
            buyer=buyer,
            seller=seller,
            offer_price=offer_price,
            target_close_date=kwargs.get('target_close_date', 
                                       timezone.now().date() + timezone.timedelta(days=30)),
            notes=kwargs.get('notes', ''),
            escrow_number=kwargs.get('escrow_number', ''),
        )
        
        # ✅ Create default milestones if not provided
        if not kwargs.get('milestones'):
            TransactionService.create_default_milestones(transaction)
        
        return transaction
    
    @staticmethod
    def create_default_milestones(transaction):
        """Create default milestone workflow for a transaction"""
        default_milestones = [
            {"name": "Offer Accepted", "order": 1, "due_days": 3},
            {"name": "Contract Signed", "order": 2, "due_days": 7},
            {"name": "Inspection Period", "order": 3, "due_days": 14},
            {"name": "Title Search", "order": 4, "due_days": 21},
            {"name": "Financing Approval", "order": 5, "due_days": 25},
            {"name": "Final Documentation", "order": 6, "due_days": 28},
            {"name": "Closing", "order": 7, "due_days": 30},
        ]
        
        start_date = timezone.now().date()
        for milestone_data in default_milestones:
            due_date = start_date + timezone.timedelta(days=milestone_data['due_days'])
            TransactionMilestone.objects.create(
                transaction=transaction,
                name=milestone_data['name'],
                order=milestone_data['order'],
                due_date=due_date,
                required=True,
            )
    
    @staticmethod
    def complete_milestone(milestone_id, completion_data=None):
        """Complete a milestone with validation"""
        milestone = TransactionMilestone.objects.get(id=milestone_id)
        
        # ✅ Check if milestone can be completed
        if milestone.transaction.status in [TransactionStatus.CLOSED, 
                                           TransactionStatus.CANCELLED]:
            raise ValidationError("Cannot complete milestones on closed/cancelled transactions.")
        
        # ✅ Complete the milestone
        completion_date = completion_data.get('completed_date') if completion_data else None
        milestone.complete(completion_date)
        
        # ✅ Add documents if provided
        if completion_data and 'document_ids' in completion_data:
            documents = Document.objects.filter(id__in=completion_data['document_ids'])
            milestone.documents.add(*documents)
        
        return milestone
    
    @staticmethod
    def close_transaction(transaction_id, agreed_price, close_date=None):
        """Close a transaction with validation"""
        transaction = Transaction.objects.get(id=transaction_id)
        
        # ✅ Check if transaction can be closed
        if transaction.status == TransactionStatus.CLOSED:
            raise ValidationError("Transaction is already closed.")
        
        if transaction.status == TransactionStatus.CANCELLED:
            raise ValidationError("Cannot close a cancelled transaction.")
        
        # ✅ Check if all required milestones are completed
        incomplete_required = transaction.milestones.filter(
            required=True,
            is_completed=False
        )
        if incomplete_required.exists():
            missing = ", ".join([m.name for m in incomplete_required])
            raise ValidationError(f"Missing required milestones: {missing}")
        
        # ✅ Close the transaction
        transaction.update_status(
            TransactionStatus.CLOSED,
            agreed_price=agreed_price,
            actual_close_date=close_date or timezone.now().date()
        )
        
        return transaction

