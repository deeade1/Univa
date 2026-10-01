from staff.models import Department


def get_department(*, department_id):
    return Department.objects.get(pk=department_id)


def list_departments():
    return Department.objects.all()


def list_active_departments():
    return Department.objects.filter(is_active=True)