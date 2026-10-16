'''from __future__ import annotations

import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.accounts.types.user import UserNode
from graphq.accounts.types.auth import MagicLoginTokenNode


class AuthQuery(graphene.ObjectType):
    sign_in = Node.Field(UserNode)
    refresh_token = Node.Field(UserNode)
    revoke_token = Node.Field(UserNode)
    verify_token = Node.Field(UserNode)
    logout = Node.Field(UserNode)
    revoke_all_tokens = Node.Field(UserNode)
    send_password_reset = Node.Field(UserNode)
    # ------------------------------------------------------------------
    # Magic links
    # ------------------------------------------------------------------
    send_magic_link = Node.Field(MagicLoginTokenNode)
    verify_magic_link = Node.Field(MagicLoginTokenNode)
    resend_magic_link = Node.Field(MagicLoginTokenNode)
    verify_face_for_magic_link = Node.Field(MagicLoginTokenNode)
    
    all_sign_in = DjangoFilterConnectionField.Field(UserNode)
    refresh_token = DjangoFilterConnectionField.Field(UserNode)
    revoke_token = DjangoFilterConnectionField.Field(UserNode)
    verify_token = DjangoFilterConnectionField.Field(UserNode)
    logout = DjangoFilterConnectionField.Field(UserNode)
    revoke_all_tokens = DjangoFilterConnectionField.Field(UserNode)
    send_password_reset = DjangoFilterConnectionField.Field(UserNode)
    # ------------------------------------------------------------------
    # Magic links
    # ------------------------------------------------------------------
    send_magic_link = DjangoFilterConnectionField.Field(MagicLoginTokenNode)
    verify_magic_link = DjangoFilterConnectionField.Field(MagicLoginTokenNode)
    resend_magic_link = DjangoFilterConnectionField.Field(MagicLoginTokenNode)
    verify_face_for_magic_link = DjangoFilterConnectionField.Field(MagicLoginTokenNode)'''