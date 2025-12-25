from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from django.template.defaultfilters import truncatechars
from decimal import Decimal
import json

from .models import (
    Product, ProductCategory, ProductTag, ProductCustomizationOption,
    ProductCustomizationChoice, Promotion, StockMovement
)


# ---------------- Inlines ----------------
class ProductCustomizationChoiceInline(admin.TabularInline):
    model = ProductCustomizationChoice
    extra = 1
    fields = ('name', 'price_modifier', 'available', 'order')
    ordering = ['order']


class ProductCustomizationOptionInline(admin.TabularInline):
    model = ProductCustomizationOption
    extra = 1
    fields = ('name', 'type', 'required', 'order')
    ordering = ['order']


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = (
        'product_name', 'movement_type_display', 'quantity',
        'previous_quantity', 'new_quantity', 'created_at_formatted'
    )
    fields = (
        'movement_type_display', 'quantity', 'previous_quantity',
        'new_quantity', 'reason', 'reference', 'created_at_formatted'
    )
    can_delete = False
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Produto'
    
    def movement_type_display(self, obj):
        return obj.get_movement_type_display()
    movement_type_display.short_description = 'Tipo'
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_formatted.short_description = 'Data'


# ---------------- Actions ----------------
def activate_products(modeladmin, request, queryset):
    queryset.update(active=True, status='active')
    messages.success(request, f'{queryset.count()} produto(s) ativado(s)')
activate_products.short_description = 'Ativar produtos selecionados'


def deactivate_products(modeladmin, request, queryset):
    queryset.update(active=False)
    messages.success(request, f'{queryset.count()} produto(s) desativado(s)')
deactivate_products.short_description = 'Desativar produtos selecionados'


def mark_as_featured(modeladmin, request, queryset):
    queryset.update(featured=True)
    messages.success(request, f'{queryset.count()} produto(s) marcado(s) como destaque')
mark_as_featured.short_description = 'Marcar como destaque'


def remove_from_featured(modeladmin, request, queryset):
    queryset.update(featured=False)
    messages.success(request, f'{queryset.count()} produto(s) removido(s) dos destaques')
remove_from_featured.short_description = 'Remover dos destaques'


def apply_discount_10(modeladmin, request, queryset):
    for product in queryset:
        product.promotional_price = product.sale_price * Decimal('0.90')
        product.save()
    messages.success(request, f'Desconto de 10% aplicado a {queryset.count()} produto(s)')
apply_discount_10.short_description = 'Aplicar 10%% de desconto'


def update_stock(modeladmin, request, queryset):
    """Ação personalizada para atualizar estoque"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        reason = request.POST.get('reason', 'Ajuste via admin')
        
        for product in queryset:
            if product.manage_stock:
                previous = product.stock_quantity
                product.stock_quantity = quantity
                product.save()
                
                # Registra movimentação
                StockMovement.objects.create(
                    product=product,
                    movement_type='adjustment',
                    quantity=quantity - previous,
                    previous_quantity=previous,
                    new_quantity=quantity,
                    reason=reason,
                    created_by=request.user.get_full_name()
                )
        
        messages.success(request, f'Estoque atualizado para {queryset.count()} produto(s)')
        return redirect(request.get_full_path())
    
    return render(request, 'admin/products/product/update_stock.html', {
        'products': queryset,
        'title': 'Atualizar Estoque'
    })
update_stock.short_description = 'Atualizar estoque'


# ---------------- Admin Classes ----------------
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'product_count', 'order', 'status_badge',
        'show_in_menu_badge', 'created_at_formatted'
    )
    list_display_links = ('name',)
    list_editable = ('order',)
    list_filter = ('active', 'show_in_menu')
    search_fields = ('name', 'description', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    actions = ['activate_categories', 'deactivate_categories']
    
    fieldsets = (
        ('📋 INFORMAÇÕES BÁSICAS', {
            'fields': ('name', 'slug', 'description', 'order')
        }),
        ('⚙️ CONFIGURAÇÕES', {
            'fields': ('active', 'show_in_menu', 'icon')
        }),
    )
    
    def product_count(self, obj):
        count = obj.products.count()
        return format_html(
            '<span class="badge" style="background:#6c757d;color:white;padding:2px 8px;border-radius:10px">{}</span>',
            count
        )
    product_count.short_description = 'Qtd. Produtos'
    
    def status_badge(self, obj):
        color = 'green' if obj.active else 'gray'
        text = 'Ativa' if obj.active else 'Inativa'
        return format_html(
            '<span class="badge" style="background:{};color:white;padding:2px 8px;border-radius:10px">{}</span>',
            color, text
        )
    status_badge.short_description = 'Status'
    
    def show_in_menu_badge(self, obj):
        color = 'blue' if obj.show_in_menu else 'lightgray'
        text = 'Sim' if obj.show_in_menu else 'Não'
        text_color = 'white' if obj.show_in_menu else 'black'
        return format_html(
            '<span class="badge" style="background:{};color:{};padding:2px 8px;border-radius:10px">{}</span>',
            color, text_color, text
        )
    show_in_menu_badge.short_description = 'No Menu'
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    created_at_formatted.short_description = 'Criada em'
    
    def activate_categories(self, request, queryset):
        queryset.update(active=True)
        messages.success(request, f'{queryset.count()} categoria(s) ativada(s)')
    activate_categories.short_description = 'Ativar categorias selecionadas'
    
    def deactivate_categories(self, request, queryset):
        queryset.update(active=False)
        messages.success(request, f'{queryset.count()} categoria(s) desativada(s)')
    deactivate_categories.short_description = 'Desativar categorias selecionadas'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name_sku', 'category_badge', 'price_info',
        'stock_badge', 'status_badge', 'featured_badge',
        'profit_margin_display', 'updated_at_formatted', 'quick_actions'
    )
    
    list_display_links = ('name_sku',)
    list_editable = ()
    
    list_filter = (
        'status', 'category', 'featured', 'active', 
        'allow_customizations', 'manage_stock'
    )
    
    search_fields = (
        'name', 'sku', 'description', 'category__name',
        'tags__name'
    )
    
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    readonly_fields = (
        'sku', 'slug', 'created_at', 'updated_at',
        'current_price_display', 'profit_margin_display',
        'discount_percentage_display', 'stock_status_info',
        'has_promotion_badge', 'total_sold', 'revenue_generated',
        'image_preview'
    )
    
    fieldsets = (
        ('📋 INFORMAÇÕES BÁSICAS', {
            'fields': (
                ('name', 'sku', 'slug'),
                'category', 'tags',
                ('short_description', 'description')
            )
        }),
        
        ('💰 PREÇOS', {
            'fields': (
                ('cost_price', 'sale_price'),
                'promotional_price',
                ('current_price_display', 'profit_margin_display'),
                'discount_percentage_display'
            )
        }),
        
        ('📊 STATUS E CONTROLE', {
            'fields': (
                ('status', 'active'),
                ('featured', 'order'),
                ('allow_customizations', 'max_customizations')
            )
        }),
        
        ('📦 ESTOQUE', {
            'fields': (
                ('manage_stock', 'stock_quantity'),
                'low_stock_threshold',
                'stock_status_info'
            ),
            'classes': ('collapse',)
        }),
        
        ('🍎 INFORMAÇÕES NUTRICIONAIS', {
            'fields': ('calories', 'preparation_time'),
            'classes': ('collapse',)
        }),
        
        ('🖼️ IMAGENS', {
            'fields': ('image_preview', 'image', 'additional_images'),
            'classes': ('collapse',)
        }),
        
        ('📈 ESTATÍSTICAS', {
            'fields': (
                'has_promotion_badge',
                ('total_sold', 'revenue_generated'),
                ('created_at', 'updated_at')
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ProductCustomizationOptionInline, StockMovementInline]
    
    actions = [
        activate_products, deactivate_products,
        mark_as_featured, remove_from_featured,
        apply_discount_10, update_stock,
        'export_products_csv', 'print_product_labels'
    ]
    
    # ---------------- Campos personalizados ----------------
    def name_sku(self, obj):
        return format_html(
            '<div><strong>{}</strong><br/><small style="color:#666">{}</small></div>',
            obj.name, obj.sku
        )
    name_sku.short_description = 'Produto (SKU)'
    
    def category_badge(self, obj):
        if obj.category:
            return format_html(
                '<span class="badge" style="background:#6f42c1;color:white;padding:2px 8px;border-radius:10px">{}</span>',
                obj.category.name
            )
        return '-'
    category_badge.short_description = 'Categoria'
    
    def price_info(self, obj):
        if obj.has_promotion:
            return format_html(
                '<div><span style="text-decoration:line-through;color:#999">R$ {}</span><br/>'
                '<strong style="color:#d33">R$ {}</strong></div>',
                obj.sale_price, obj.current_price
            )
        return format_html('<strong>R$ {}</strong>', obj.current_price)
    price_info.short_description = 'Preço'
    
    def stock_badge(self, obj):
        if not obj.manage_stock:
            return mark_safe(
                '<span class="badge" style="background:#17a2b8;color:white;padding:2px 8px;border-radius:10px">NC</span>'
            )
        
        if obj.stock_quantity <= 0:
            return mark_safe(
                '<span class="badge" style="background:#dc3545;color:white;padding:2px 8px;border-radius:10px">Esgotado</span>'
            )
        elif obj.stock_quantity <= obj.low_stock_threshold:
            return format_html(
                '<span class="badge" style="background:#ffc107;color:black;padding:2px 8px;border-radius:10px">Baixo ({})</span>',
                obj.stock_quantity
            )
        else:
            return format_html(
                '<span class="badge" style="background:#28a745;color:white;padding:2px 8px;border-radius:10px">{}</span>',
                obj.stock_quantity
            )
    stock_badge.short_description = 'Estoque'
    
    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'inactive': 'gray',
            'out_of_stock': 'orange',
            'coming_soon': 'blue'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span class="badge" style="background:{};color:white;padding:2px 8px;border-radius:10px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def featured_badge(self, obj):
        if obj.featured:
            return mark_safe('⭐')
        return '☆'
    featured_badge.short_description = 'Destaque'
    
    def profit_margin_display(self, obj):
        margin = obj.profit_margin
        if margin is None:
            return '-'
        color = 'green' if margin > 30 else 'orange' if margin > 15 else 'red'
        margin_formatted = f'{margin:.1f}'
        return format_html(
            '<span style="color:{};font-weight:bold">{}%</span>',
            color, margin_formatted
        )
    profit_margin_display.short_description = 'Margem %'
    
    def updated_at_formatted(self, obj):
        return obj.updated_at.strftime('%d/%m %H:%M')
    updated_at_formatted.short_description = 'Atualizado'
    
    def quick_actions(self, obj):
        return format_html(
            '<div style="white-space:nowrap">'
            '<a href="/admin/products/product/{}/change/" class="button" title="Editar">✏️</a> '
            '<a href="#" class="button" title="Ver detalhes" onclick="alert(\'Em desenvolvimento\')">👁️</a>'
            '</div>',
            obj.id
        )
    quick_actions.short_description = 'Ações'
    
    # ---------------- Readonly fields ----------------
    def current_price_display(self, obj):
        return format_html('<strong>R$ {}</strong>', obj.current_price)
    current_price_display.short_description = 'Preço Atual'
    
    def discount_percentage_display(self, obj):
        if obj.has_promotion:
            return format_html(
                '<span style="color:#28a745;font-weight:bold">-{}%</span>',
                obj.discount_percentage
            )
        return '-'
    discount_percentage_display.short_description = 'Desconto %'
    
    def stock_status_info(self, obj):
        return obj.stock_status
    stock_status_info.short_description = 'Status Estoque'
    
    def has_promotion_badge(self, obj):
        if obj.has_promotion:
            return mark_safe(
                '<span class="badge" style="background:#28a745;color:white;padding:4px 10px;border-radius:12px">'
                '🎯 PROMOÇÃO ATIVA'
                '</span>'
            )
        return '-'
    has_promotion_badge.short_description = 'Promoção'
    
    def total_sold(self, obj):
        try:
            from orders.models import OrderItem
            total = OrderItem.objects.filter(product=obj).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            return f"{total} unidades"
        except:
            return "0 unidades"
    
    def revenue_generated(self, obj):
        try:
            from orders.models import OrderItem
            revenue = OrderItem.objects.filter(product=obj).aggregate(
                total=Sum('subtotal')
            )['total'] or Decimal('0.00')
            return f"R$ {revenue:.2f}"
        except:
            return "R$ 0.00"
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:200px;border-radius:8px" />',
                obj.image.url
            )
        return "Sem imagem"
    image_preview.short_description = 'Pré-visualização'
    
    # ---------------- URLs customizadas ----------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='product_dashboard'),
            path('low-stock/', self.admin_site.admin_view(self.low_stock_view), name='low_stock_report'),
            path('bulk-edit/', self.admin_site.admin_view(self.bulk_edit_view), name='bulk_edit_products'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Dashboard de produtos"""
        from django.db import models
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Estatísticas básicas
        total_products = Product.objects.count()
        active_products = Product.objects.filter(active=True).count()
        out_of_stock = Product.objects.filter(
            manage_stock=True, stock_quantity=0
        ).count()
        low_stock_products = Product.objects.filter(
            manage_stock=True,
            stock_quantity__gt=0,
            stock_quantity__lte=models.F('low_stock_threshold')
        ).count()
        
        # Produtos por categoria
        by_category = ProductCategory.objects.annotate(
            product_count=Count('products')
        ).filter(product_count__gt=0).order_by('-product_count')[:10]
        
        # Produtos mais vendidos
        try:
            from orders.models import OrderItem
            top_selling = OrderItem.objects.values(
                'product__name'
            ).annotate(
                total_sold=Sum('quantity')
            ).order_by('-total_sold')[:10]
        except:
            top_selling = []
        
        # Movimentação de estoque recente
        recent_movements = StockMovement.objects.select_related(
            'product'
        ).order_by('-created_at')[:20]
        
        context = {
            'title': 'Dashboard de Produtos',
            'total_products': total_products,
            'active_products': active_products,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock_products,
            'by_category': by_category,
            'top_selling': top_selling,
            'recent_movements': recent_movements,
            'today': today,
        }
        
        return render(request, 'admin/products/product/dashboard.html', context)
    
    def low_stock_view(self, request):
        """Relatório de estoque baixo"""
        from django.db import models
        low_stock_products = Product.objects.filter(
            manage_stock=True,
            stock_quantity__gt=0,
            stock_quantity__lte=models.F('low_stock_threshold')
        ).order_by('stock_quantity')
        
        out_of_stock = Product.objects.filter(
            manage_stock=True,
            stock_quantity=0,
            active=True
        ).order_by('name')
        
        context = {
            'title': 'Relatório de Estoque',
            'low_stock_products': low_stock_products,
            'out_of_stock': out_of_stock,
            'total_low': low_stock_products.count(),
            'total_out': out_of_stock.count(),
        }
        
        return render(request, 'admin/products/product/low_stock_report.html', context)
    
    def bulk_edit_view(self, request):
        """Edição em massa de produtos"""
        if request.method == 'POST':
            product_ids = request.POST.getlist('product_ids')
            field = request.POST.get('field')
            value = request.POST.get('value')
            
            if field and value and product_ids:
                if field in ['featured', 'active']:
                    value = value.lower() in ['true', '1', 'yes', 'sim']
                
                update_kwargs = {field: value}
                Product.objects.filter(id__in=product_ids).update(**update_kwargs)
                messages.success(request, f'{len(product_ids)} produto(s) atualizado(s)')
                return redirect('admin:products_product_changelist')
        
        products = Product.objects.all()[:100]
        context = {
            'title': 'Edição em Massa de Produtos',
            'products': products,
            'fields': [
                ('category', 'Categoria'),
                ('status', 'Status'),
                ('featured', 'Destaque'),
                ('active', 'Ativo'),
            ]
        }
        
        return render(request, 'admin/products/product/bulk_edit.html', context)
    
    # ---------------- Ações ----------------
    def export_products_csv(self, request, queryset):
        """Exporta produtos selecionados para CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="produtos_export.csv"'
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'SKU', 'Nome', 'Categoria', 'Preço Venda',
            'Preço Promoção', 'Estoque', 'Status', 'Ativo'
        ])
        
        for product in queryset:
            writer.writerow([
                product.sku,
                product.name,
                product.category.name if product.category else '',
                str(product.sale_price),
                str(product.promotional_price) if product.promotional_price else '',
                product.stock_quantity if product.manage_stock else 'N/A',
                product.get_status_display(),
                'Sim' if product.active else 'Não'
            ])
        
        return response
    export_products_csv.short_description = 'Exportar CSV'
    
    def print_product_labels(self, request, queryset):
        """Gera etiquetas para produtos"""
        messages.success(request, f'{queryset.count()} etiqueta(s) preparada(s) para impressão')
    print_product_labels.short_description = 'Imprimir etiquetas'


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_display', 'product_count', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    
    def color_display(self, obj):
        return format_html(
            '<div style="display:flex;align-items:center">'
            '<div style="width:20px;height:20px;background:{};border-radius:3px;margin-right:8px"></div>'
            '<span>{}</span>'
            '</div>',
            obj.color, obj.color
        )
    color_display.short_description = 'Cor'
    
    def product_count(self, obj):
        count = obj.product_set.count()
        return format_html(
            '<span class="badge" style="background:#6c757d;color:white;padding:2px 8px;border-radius:10px">{}</span>',
            count
        )
    product_count.short_description = 'Produtos'


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'type_badge', 'discount_display',
        'status_badge', 'products_count', 'time_remaining_display',
        'usage_display', 'created_at_formatted'
    )
    
    list_filter = ('active', 'promotion_type')
    search_fields = ('name', 'description')
    filter_horizontal = ('products', 'categories')
    date_hierarchy = 'start_date'
    
    readonly_fields = (
        'slug', 'times_used', 'created_at', 'updated_at',
        'status_display', 'time_remaining_display',
        'affected_products_count'
    )
    
    fieldsets = (
        ('📋 INFORMAÇÕES BÁSICAS', {
            'fields': ('name', 'slug', 'description', 'promotion_type')
        }),
        
        ('💰 DESCONTO', {
            'fields': (
                'discount_value',
                ('minimum_order_value', 'maximum_discount'),
                'priority'
            )
        }),
        
        ('🎯 APLICAÇÃO', {
            'fields': ('products', 'categories')
        }),
        
        ('⏰ PERÍODO', {
            'fields': ('start_date', 'end_date')
        }),
        
        ('⚙️ CONTROLE', {
            'fields': (
                'active',
                ('usage_limit', 'times_used'),
                'status_display',
                'time_remaining_display'
            )
        }),
        
        ('📊 ESTATÍSTICAS', {
            'fields': ('affected_products_count', ('created_at', 'updated_at'))
        }),
    )
    
    actions = ['activate_promotions', 'deactivate_promotions', 'duplicate_promotions']
    
    def type_badge(self, obj):
        colors = {
            'percentage': '#17a2b8',
            'fixed': '#28a745',
            'bundle': '#ffc107'
        }
        text_colors = {
            'percentage': 'white',
            'fixed': 'white',
            'bundle': 'black'
        }
        color = colors.get(obj.promotion_type, '#6c757d')
        text_color = text_colors.get(obj.promotion_type, 'white')
        
        return format_html(
            '<span class="badge" style="background:{};color:{};padding:2px 8px;border-radius:10px">{}</span>',
            color, text_color, obj.get_promotion_type_display()
        )
    type_badge.short_description = 'Tipo'
    
    def discount_display(self, obj):
        if obj.promotion_type == 'percentage':
            return f"{obj.discount_value}%"
        return f"R$ {obj.discount_value}"
    discount_display.short_description = 'Desconto'
    
    def status_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="badge" style="background:#28a745;color:white;padding:2px 8px;border-radius:10px">'
                'ATIVA'
                '</span>'
            )
        else:
            return mark_safe(
                '<span class="badge" style="background:#6c757d;color:white;padding:2px 8px;border-radius:10px">'
                'INATIVA'
                '</span>'
            )
    status_badge.short_description = 'Status'
    
    def products_count(self, obj):
        count = obj.products.count()
        return format_html(
            '<span class="badge" style="background:#17a2b8;color:white;padding:2px 8px;border-radius:10px">{}</span>',
            count
        )
    products_count.short_description = 'Produtos'
    
    def time_remaining_display(self, obj):
        if not obj.is_active:
            return '-'
        
        remaining = obj.time_remaining
        if remaining:
            days = remaining.days
            hours = remaining.seconds // 3600
            
            if days > 0:
                return f"{days} dia(s)"
            elif hours > 0:
                return f"{hours} hora(s)"
            else:
                return "Menos de 1 hora"
        return '-'
    time_remaining_display.short_description = 'Tempo Restante'
    
    def usage_display(self, obj):
        if obj.usage_limit:
            return f"{obj.times_used}/{obj.usage_limit}"
        return f"{obj.times_used}"
    usage_display.short_description = 'Uso'
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    created_at_formatted.short_description = 'Criada em'
    
    def status_display(self, obj):
        now = timezone.now()
        if not obj.start_date or not obj.end_date:
            return format_html(
                '<span style="color:#ffc107">⚠️ Datas não definidas</span>'
        )
        
        if obj.start_date > now:
            return format_html(
                '<span style="color:#17a2b8">🕐 Programada (inicia em {})</span>',
                obj.start_date.strftime('%d/%m/%Y %H:%M')
            )
        elif obj.end_date < now:
            return format_html(
                '<span style="color:#6c757d">⏹️ Expirada (terminou em {})</span>',
                obj.end_date.strftime('%d/%m/%Y %H:%M')
            )
        elif obj.is_active:
            return format_html(
                '<span style="color:#28a745">✅ Ativa (termina em {})</span>',
                obj.end_date.strftime('%d/%m/%Y %H:%M')
            )
        else:
            return mark_safe('<span style="color:#dc3545">❌ Inativa</span>')
    status_display.short_description = 'Status Detalhado'
    
    def affected_products_count(self, obj):
        from_products = obj.products.count()
        from_categories = Product.objects.filter(
            category__in=obj.categories.all()
        ).count()
        total = from_products + from_categories
        
        return format_html(
            '<div>'
            '<p>🎯 <strong>{} produto(s) no total</strong></p>'
            '<small style="color:#666">'
            '{} da seleção direta + {} das categorias'
            '</small>'
            '</div>',
            total, from_products, from_categories
        )
    affected_products_count.short_description = 'Produtos Afetados'
    
    def activate_promotions(self, request, queryset):
        queryset.update(active=True)
        messages.success(request, f'{queryset.count()} promoção(ões) ativada(s)')
    activate_promotions.short_description = 'Ativar promoções'
    
    def deactivate_promotions(self, request, queryset):
        queryset.update(active=False)
        messages.success(request, f'{queryset.count()} promoção(ões) desativada(s)')
    deactivate_promotions.short_description = 'Desativar promoções'
    
    def duplicate_promotions(self, request, queryset):
        for promotion in queryset:
            promotion.pk = None
            promotion.name = f"{promotion.name} (Cópia)"
            promotion.slug = f"{promotion.slug}-copia"
            promotion.times_used = 0
            promotion.active = False
            promotion.save()
            
            # Copia relações ManyToMany
            promotion.products.set(promotion.products.all())
            promotion.categories.set(promotion.categories.all())
        
        messages.success(request, f'{queryset.count()} promoção(ões) duplicada(s)')
    duplicate_promotions.short_description = 'Duplicar promoções'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'product_link', 'movement_type_badge', 'quantity_display',
        'previous_new_display', 'reason_short', 'created_by',
        'created_at_formatted'
    )
    
    list_filter = ('movement_type', 'created_at')
    search_fields = ('product__name', 'product__sku', 'reason', 'reference')
    date_hierarchy = 'created_at'
    readonly_fields = ('product', 'previous_quantity', 'new_quantity')
    
    def product_link(self, obj):
        return format_html(
            '<a href="/admin/products/product/{}/change/">{}</a>',
            obj.product.id, obj.product.name
        )
    product_link.short_description = 'Produto'
    
    def movement_type_badge(self, obj):
        colors = {
            'in': '#28a745',
            'out': '#dc3545',
            'adjustment': '#ffc107',
            'return': '#17a2b8'
        }
        text_colors = {
            'in': 'white',
            'out': 'white',
            'adjustment': 'black',
            'return': 'white'
        }
        color = colors.get(obj.movement_type, '#6c757d')
        text_color = text_colors.get(obj.movement_type, 'white')
        
        return format_html(
            '<span class="badge" style="background:{};color:{};padding:2px 8px;border-radius:10px">{}</span>',
            color, text_color, obj.get_movement_type_display()
        )
    movement_type_badge.short_description = 'Tipo'
    
    def quantity_display(self, obj):
        if obj.quantity >= 0:
            return format_html(
                '<span style="color:#28a745">+{}</span>',
                obj.quantity
            )
        else:
            return format_html(
                '<span style="color:#dc3545">{}</span>',
                obj.quantity
            )
    quantity_display.short_description = 'Quantidade'
    
    def previous_new_display(self, obj):
        return format_html(
            '{} <span style="color:#666">→</span> <strong>{}</strong>',
            obj.previous_quantity, obj.new_quantity
        )
    previous_new_display.short_description = 'Anterior → Novo'
    
    def reason_short(self, obj):
        if obj.reason and len(obj.reason) > 30:
            return f"{obj.reason[:30]}..."
        return obj.reason or '-'
    reason_short.short_description = 'Motivo'
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_formatted.short_description = 'Data'