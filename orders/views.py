# No admin.py, adicione este método ao OrderAdmin:
def dashboard_view(self, request):
    from django.db.models import Count, Sum, Avg
    from django.utils.timezone import now, timedelta
    from django.core.serializers.json import DjangoJSONEncoder
    import json
    
    today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now() - timedelta(days=7)
    
    # Estatísticas básicas
    orders_today = Order.objects.filter(created_at__gte=today_start)
    total_orders_today = orders_today.count()
    
    # Receita do dia
    total_revenue_today = orders_today.filter(
        payment_status='paid'
    ).aggregate(Sum('total'))['total__sum'] or 0
    
    # Pedidos por status
    orders_by_status = orders_today.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Tempo médio de preparo
    avg_preparation_time = Order.objects.filter(
        prepared_at__isnull=False,
        created_at__gte=today_start
    ).annotate(
        prep_time=models.ExpressionWrapper(
            models.F('prepared_at') - models.F('created_at'),
            output_field=models.DurationField()
        )
    ).aggregate(
        avg=Avg('prep_time')
    )['avg']
    
    if avg_preparation_time:
        avg_preparation_time = avg_preparation_time.total_seconds() / 60
    
    # Produtos mais vendidos
    top_products = OrderItem.objects.filter(
        order__created_at__gte=today_start
    ).values('product__name').annotate(
        total=Sum('quantity'),
        revenue=Sum(models.F('quantity') * models.F('unit_price'))
    ).order_by('-total')[:10]
    
    # Vendas últimos 7 dias
    sales_data = Order.objects.filter(
        created_at__gte=week_ago
    ).annotate(
        day=models.functions.TruncDay('created_at')
    ).values('day').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('day')
    
    # Pedidos recentes
    recent_orders = Order.objects.all().order_by('-created_at')[:20]
    
    # Converter QuerySets para JSON
    from django.core.serializers import serialize
    import json
    from django.db.models import Model
    
    class EnhancedJSONEncoder(DjangoJSONEncoder):
        def default(self, obj):
            if isinstance(obj, Model):
                return str(obj)
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return super().default(obj)
    
    context = {
        'title': 'Dashboard de Pedidos',
        'today': now().date(),
        'total_orders_today': total_orders_today,
        'total_revenue_today': total_revenue_today,
        'orders_by_status': orders_by_status,
        'orders_by_status_json': json.dumps(list(orders_by_status), cls=EnhancedJSONEncoder),
        'avg_preparation_time': avg_preparation_time,
        'top_products': top_products,
        'sales_data': sales_data,
        'sales_data_json': json.dumps(list(sales_data), cls=EnhancedJSONEncoder),
        'recent_orders': recent_orders,
        'opts': self.model._meta,
    }
    
    # Se for requisição AJAX para refresh
    if request.GET.get('refresh'):
        return JsonResponse({
            'total_orders_today': total_orders_today,
            'total_revenue_today': float(total_revenue_today),
            'avg_preparation_time': avg_preparation_time,
        })
    
    return TemplateResponse(request, 'admin/orders/order/dashboard.html', context)