from notifications.events import constants
from notifications.events.emitter import emit_notification_event


def emit_staff_member_created(*, staff_member):
    return emit_notification_event(
        event_type=constants.STAFF_MEMBER_CREATED,
        module="staff",
        actor=None,
        object_type="StaffMember",
        object_id=staff_member.pk,
        payload={
            "staff_member_id": staff_member.pk,
            "employee_number": staff_member.employee_number,
            "department_id": staff_member.department_id,
            "position_id": staff_member.position_id,
            "employment_status": staff_member.employment_status,
            "recipient_id": staff_member.user_id,
        },
    )


def emit_staff_member_employment_status_changed(
    *,
    staff_member,
    previous_status,
):
    return emit_notification_event(
        event_type=constants.STAFF_MEMBER_EMPLOYMENT_STATUS_CHANGED,
        module="staff",
        actor=None,
        object_type="StaffMember",
        object_id=staff_member.pk,
        payload={
            "staff_member_id": staff_member.pk,
            "employee_number": staff_member.employee_number,
            "previous_status": previous_status,
            "new_status": staff_member.employment_status,
            "date_left": (
                staff_member.date_left.isoformat()
                if staff_member.date_left
                else None
            ),
            "recipient_id": staff_member.user_id,
        },
    )