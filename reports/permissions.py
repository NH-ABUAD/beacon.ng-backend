from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        owner_id = None
        if hasattr(obj, 'reporter_id'):
            owner_id = obj.reporter_id
        elif hasattr(obj, 'report') and obj.report is not None:
            owner_id = obj.report.reporter_id

        return bool(owner_id is not None and owner_id == request.user.id)


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))
