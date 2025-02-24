# apps/approval_chain/admin.py

from django.contrib import admin
from .models import ApprovalChain, Approver


@admin.register(ApprovalChain)
class ApprovalChainAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name", "created_by__username")
    ordering = ("-created_at",)


@admin.register(Approver)
class ApproverAdmin(admin.ModelAdmin):
    list_display = ("user", "approval_chain", "order", "status", "is_current")
    search_fields = ("user__username", "approval_chain__name")
    list_filter = ("status", "approval_chain")
    ordering = ("approval_chain", "order")
