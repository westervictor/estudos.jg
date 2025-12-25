from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Order
from django.utils import timezone


class OrderStatusFilter(admin.SimpleListFilter):
    title = _('Status do Pedido')
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        return Order.STATUS_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class OrderPriorityFilter(admin.SimpleListFilter):
    title = _('Prioridade')
    parameter_name = 'priority'
    
    def lookups(self, request, model_admin):
        return Order.PRIORITY_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(priority=self.value())
        return queryset


class PaymentStatusFilter(admin.SimpleListFilter):
    title = _('Status do Pagamento')
    parameter_name = 'payment_status'
    
    def lookups(self, request, model_admin):
        return [
            ('pending', _('Pendente')),
            ('paid', _('Pago')),
            ('refunded', _('Reembolsado')),
        ]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_status=self.value())
        return queryset


class DeliveryFilter(admin.SimpleListFilter):
    title = _('Tipo de Pedido')
    parameter_name = 'is_delivery'
    
    def lookups(self, request, model_admin):
        return [
            ('delivery', _('Entrega')),
            ('pickup', _('Retirada')),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'delivery':
            return queryset.filter(is_delivery=True)
        elif self.value() == 'pickup':
            return queryset.filter(is_delivery=False)
        return queryset


class OrderDateFilter(admin.SimpleListFilter):
    title = _('Data do Pedido')
    parameter_name = 'date_range'
    
    def lookups(self, request, model_admin):
        return [
            ('today', _('Hoje')),
            ('yesterday', _('Ontem')),
            ('this_week', _('Esta semana')),
            ('last_week', _('Semana passada')),
            ('this_month', _('Este mês')),
            ('last_month', _('Mês passado')),
        ]
    
    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'today':
            return queryset.filter(created_at__date=now.date())
        elif self.value() == 'yesterday':
            yesterday = now.date() - timezone.timedelta(days=1)
            return queryset.filter(created_at__date=yesterday)
        elif self.value() == 'this_week':
            start = now - timezone.timedelta(days=now.weekday())
            return queryset.filter(created_at__gte=start.replace(hour=0, minute=0, second=0))
        elif self.value() == 'last_week':
            start = now - timezone.timedelta(days=now.weekday() + 7)
            end = start + timezone.timedelta(days=7)
            return queryset.filter(created_at__range=[start, end])
        elif self.value() == 'this_month':
            return queryset.filter(
                created_at__year=now.year,
                created_at__month=now.month
            )
        elif self.value() == 'last_month':
            last_month = now.month - 1 if now.month > 1 else 12
            year = now.year if now.month > 1 else now.year - 1
            return queryset.filter(
                created_at__year=year,
                created_at__month=last_month
            )
        return queryset