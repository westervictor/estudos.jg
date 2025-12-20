from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay

from .models import Order, OrderItem, OrderItemCustomization, OrderStatusHistory
from .filters import (
    OrderStatusFilter, OrderPriorityFilter, PaymentStatusFilter,
    DeliveryFilter, OrderDateFilter
)

# ---------------- Inlines ----------------
class OrderItemCustomizationInline(admin.TabularInline):
    model = OrderItemCustomization
    extra = 0
    readonly_fields = ('description',)
    fields = ('option', 'choice', 'extra_price', 'description')
    can_delete = False
    
    def description(self, obj):
        return obj.description
    description.short_description = 'Descrição'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_info', 'subtotal_display', 'unit_price_display', 'customizations_summary')
    fields = ('product_info', 'quantity', 'unit_price_display', 'subtotal_display', 'special_instructions', 'customizations_summary')
    
    @admin.display(description='Produto')
    def product_info(self, obj):
        if obj.product:
            return f"{obj.product.name} ({obj.product.category})"
        return "-"
    
    @admin.display(description='Subtotal')
    def subtotal_display(self, obj):
        return f"R$ {obj.subtotal:.2f}" if obj.subtotal is not None else "-"
    
    @admin.display(description='Preço Unit.')
    def unit_price_display(self, obj):
        if obj.unit_price is not None:
            return f"R$ {obj.unit_price:.2f}"
        return "-"
    
    @admin.display(description='Personalizações')
    def customizations_summary(self, obj):
        customs = obj.customizations.all()
        if customs:
            return ", ".join([str(c) for c in customs])
        return "-"


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('status_change', 'changed_by', 'changed_at')
    fields = ('status_change', 'changed_by', 'changed_at', 'notes')
    can_delete = False
    
    @admin.display(description='Alteração')
    def status_change(self, obj):
        old = dict(Order.STATUS_CHOICES).get(obj.old_status, obj.old_status)
        new = dict(Order.STATUS_CHOICES).get(obj.new_status, obj.new_status)
        return f"{old} → {new}"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'status_badge', 'customer_info', 'item_count',
        'total_display', 'payment_status_badge', 'created_at_formatted',
        'priority_badge', 'order_actions'
    )

    list_display_links = ('order_number',)
    
    list_filter = (
        OrderStatusFilter, OrderPriorityFilter, PaymentStatusFilter,
        DeliveryFilter, OrderDateFilter,
    )
    search_fields = (
        'order_number', 'customer_name', 'customer_phone',
        'items__product__name', 'delivery_address'
    )
    list_per_page = 25
    date_hierarchy = 'created_at'

    readonly_fields = (
        'order_number', 'created_at', 'updated_at',
        'prepared_at', 'delivered_at', 'subtotal_display',
        'delivery_fee_display', 'tax_display', 'discount_display',
        'total_display', 'item_count', 'preparation_time_display',
        'status_history_summary'
    )

    fieldsets = (
        ('📋 INFORMAÇÕES DO PEDIDO', {
            'fields': ('order_number', ('status', 'priority'), ('created_at', 'updated_at'))
        }),
        ('👤 DADOS DO CLIENTE', {
            'fields': ('customer_name', 'customer_phone', ('is_delivery', 'delivery_address'))
        }),
        ('💰 VALORES', {
            'fields': (('subtotal_display', 'delivery_fee_display'), ('tax_display', 'discount_display'), 'total_display')
        }),
        ('💳 PAGAMENTO', {
            'fields': (('payment_method', 'payment_status'),)
        }),
        ('⏰ TEMPOS', {
            'fields': ('estimated_time', ('prepared_at', 'delivered_at'), 'preparation_time_display')
        }),
        ('📝 OBSERVAÇÕES', {'fields': ('notes',)}),
        ('📊 ESTATÍSTICAS', {'fields': ('item_count', 'status_history_summary')}),  
    )

    inlines = [OrderItemInline, OrderStatusHistoryInline]

    actions = [
        'mark_as_preparing', 'mark_as_ready', 'mark_as_delivered',
        'mark_as_paid', 'export_orders_json', 'print_kitchen_tickets'
    ]

    # ---------------- URLs Customizadas ----------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/change_status/<str:new_status>/', self.admin_site.admin_view(self.change_status_view), name='order_change_status'),
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='order_dashboard'),
            path('kitchen/', self.admin_site.admin_view(self.kitchen_view), name='kitchen_view'),
        ]
        return custom_urls + urls

    # ---------------- Views ----------------
    @admin.display(description='Cliente')
    def customer_info(self, obj):
        if obj.customer_name:
            phone = f"📱 {obj.customer_phone}" if obj.customer_phone else ""
            return format_html('<div><strong>{}</strong><br/><small>{}</small></div>', obj.customer_name, phone)
        return "Cliente não identificado"

    def kitchen_view(self, request):
        orders = Order.objects.filter(status='preparing').order_by('created_at')
        return render(request, 'admin/orders/order/kitchen_view.html', {'orders': orders, 'title': 'Comanda da Cozinha'})

    def change_status_view(self, request, object_id, new_status):
        try:
            order = Order.objects.get(id=object_id)
            order.change_status(new_status, user=request.user.get_full_name())
            messages.success(request, f'Status alterado para {new_status}')
        except Exception as e:
            messages.error(request, str(e))
        return redirect('admin:orders_order_change', object_id)

    def dashboard_view(self, request):
        from django.db.models import Avg
        from django.utils.timezone import now, timedelta

        today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
        sales_data = Order.objects.filter(created_at__gte=now()-timedelta(days=7)).annotate(day=TruncDay('created_at')).values('day').annotate(total=Sum('total'), count=Count('id')).order_by('day')

        context = {
            'title': 'Dashboard de Pedidos',
            'today': now().date(),
            'last_7_days': now().date() - timedelta(days=7),
            'total_orders_today': Order.objects.filter(created_at__gte=today_start).count(),
            'total_revenue_today': Order.objects.filter(created_at__gte=today_start, payment_status='paid').aggregate(Sum('total'))['total__sum'] or 0,
            'orders_by_status': Order.objects.filter(created_at__gte=today_start).values('status').annotate(count=Count('id')),
            'avg_preparation_time': Order.objects.filter(prepared_at__isnull=False, created_at__gte=today_start).aggregate(avg=Avg('preparation_time'))['avg'] or 0,
            'top_products': OrderItem.objects.filter(order__created_at__gte=today_start).values('product__name').annotate(total=Sum('quantity')).order_by('-total')[:10],
            'sales_data': list(sales_data),
        }
        return render(request, self.dashboard_template, context)

    # ---------------- Métodos Readonly e Badges ----------------
    @admin.display(description='Subtotal')
    def subtotal_display(self, obj):
        return f"R$ {obj.subtotal:.2f}" if obj.subtotal else "-"
    
    @admin.display(description='Taxa de Entrega')
    def delivery_fee_display(self, obj):
        return f"R$ {obj.delivery_fee:.2f}" if obj.delivery_fee else "-"
    
    @admin.display(description='Impostos')
    def tax_display(self, obj):
        return f"R$ {obj.tax:.2f}" if obj.tax else "-"
    
    @admin.display(description='Desconto')
    def discount_display(self, obj):
        return f"- R$ {obj.discount:.2f}" if obj.discount else "-"
    
    @admin.display(description='Total')
    def total_display(self, obj):
        return f"R$ {obj.total:.2f}" if obj.total else "-"
    
    @admin.display(description='Tempo de Preparo')
    def preparation_time_display(self, obj):
        return f"{obj.preparation_time} minutos" if obj.preparation_time else "Ainda não preparado"
    
    @admin.display(description='Últimas Alterações')
    def status_history_summary(self, obj):
        history = obj.status_history.all()[:5]
        if not history:
            return "Sem histórico"
        return format_html("<br>".join(
            f"{h.changed_at.strftime('%H:%M')}: {h.get_old_status_display()} → {h.get_new_status_display()}"
            for h in history
        ))

    @admin.display(description='Criado em', ordering='created_at')
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')

    @admin.display(description='Ações')
    def order_actions(self, obj):
        return format_html("Botões aqui")

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'open':'blue','preparing':'orange','ready':'green','out_for_delivery':'purple','delivered':'gray','cancelled':'red'}
        color = colors.get(obj.status,'blue')
        return format_html('<span class="badge" style="background-color:{};color:white;padding:2px 8px;border-radius:10px">{}</span>', color, obj.get_status_display())

    @admin.display(description='Pagamento')
    def payment_status_badge(self, obj):
        colors = {'pending':'orange','paid':'green','refunded':'red'}
        color = colors.get(obj.payment_status,'gray')
        return format_html('<span class="badge" style="background-color:{};color:white;padding:2px 8px;border-radius:10px">{}</span>', color, obj.get_payment_status_display())

    @admin.display(description='Prioridade')
    def priority_badge(self, obj):
        colors = {'normal':'blue','urgent':'orange','priority':'red'}
        color = colors.get(obj.priority,'blue')
        return format_html('<span class="badge" style="background-color:{};color:white;padding:2px 8px;border-radius:10px">{}</span>', color, obj.get_priority_display())

    # ---------------- Ações ----------------
    def mark_as_preparing(self, request, queryset):
        updated = 0
        for order in queryset:
            try:
                order.change_status('preparing', user=request.user.get_full_name())
                updated += 1
            except: pass
        self.message_user(request, f'{updated} pedido(s) marcado(s) como "Em preparo"')
    mark_as_preparing.short_description = '📝 Marcar como Em Preparo'

    def mark_as_ready(self, request, queryset):
        updated = 0
        for order in queryset.filter(status='preparing'):
            try:
                order.change_status('ready', user=request.user.get_full_name())
                updated += 1
            except: pass
        self.message_user(request, f'{updated} pedido(s) marcado(s) como "Pronto"')
    mark_as_ready.short_description = '✅ Marcar como Pronto'

    def mark_as_delivered(self, request, queryset):
        updated = 0
        for order in queryset.filter(status='ready'):
            try:
                order.change_status('delivered', user=request.user.get_full_name())
                updated += 1
            except: pass
        self.message_user(request, f'{updated} pedido(s) marcado(s) como "Entregue"')
    mark_as_delivered.short_description = '📦 Marcar como Entregue'

    def mark_as_paid(self, request, queryset):
        queryset.update(payment_status='paid')
        self.message_user(request, f'{queryset.count()} pedido(s) marcado(s) como "Pago"')
    mark_as_paid.short_description = '💳 Marcar como Pago'

    def export_orders_json(self, request, queryset):
        import json
        from django.http import HttpResponse
        data = []
        for order in queryset:
            data.append({
                'order_number': order.order_number,
                'customer': order.customer_name,
                'total': str(order.total),
                'status': order.status,
                'items':[{'product':i.product.name,'quantity':i.quantity,'subtotal':str(i.subtotal)} for i in order.items.all()]
            })
        response = HttpResponse(json.dumps(data, indent=2, ensure_ascii=False), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=orders_export.json'
        return response
    export_orders_json.short_description = '📤 Exportar JSON'

    def print_kitchen_tickets(self, request, queryset):
        self.message_user(request, f'{queryset.count()} comanda(s) enviada(s) para impressão')
    print_kitchen_tickets.short_description = '🖨️ Imprimir Comandas'

    dashboard_template = 'admin/orders/order/dashboard.html'

    class Media:
        css = {'all': ('admin/css/order_admin.css',)}
        js = ('admin/js/order_admin.js','https://cdn.jsdelivr.net/npm/chart.js',)
