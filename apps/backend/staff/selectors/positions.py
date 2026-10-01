from staff.models import Department, Position


def get_position(*, position_id):
    return Position.objects.get(pk=position_id)


def list_positions():
    return Position.objects.all()


def list_active_positions():
    return Position.objects.filter(is_active=True)


def list_positions_by_department(*, department):
    if not isinstance(department, Department):
        raise TypeError("department must be a Department instance.")

    return Position.objects.filter(department=department)