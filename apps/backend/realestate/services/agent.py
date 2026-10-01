from realestate.models import AgentProfile


def get_agent_profile(user):
    return AgentProfile.objects.filter(
        profile__user=user,
    ).first()