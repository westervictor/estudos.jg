from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ProductStatusFilter(admin.SimpleListFilter):
    title = _('Status do Produto')
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        return [
            ('active', _('✅ Ativos')),
            ('inactive', _('⏸️ Inativos')),
            ('out_of_stock', _('📦 Sem estoque')),
            ('coming_soon', _('🕐 Em breve')),
            ('featured', _('⭐ Destaques')),
            ('with_promo', _('🎯 Com promoção')),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(active=True, status='active')
        elif self.value() == 'inactive':
            return queryset.filter(active=False)
        elif self.value() == 'out_of_stock':
            return queryset.filter(manage_stock=True, stock_quantity=0)
        elif self.value() == 'coming_soon':
            return queryset.filter(status='coming_soon')
        elif self.value() == 'featured':
            return queryset.filter(featured=True)
        elif self.value() == 'with_promo':
            return queryset.filter(promotional_price__isnull=False)
        return queryset


class ProductCategoryFilter(admin.RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        return field.get_choices(
            include_blank=False,
            limit_choices_to={'active': True}
        )


class ProductStockFilter(admin.SimpleListFilter):
    title = _('Situação do Estoque')
    parameter_name = 'stock_situation'
    
    def lookups(self, request, model_admin):
        return [
            ('no_control', _('🔄 Sem controle')),
            ('in_stock', _('✅ Em estoque')),
            ('low_stock', _('⚠️ Estoque baixo')),
            ('out_of_stock', _('❌ Esgotado')),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'no_control':
            return queryset.filter(manage_stock=False)
        elif self.value() == 'in_stock':
            return queryset.filter(
                manage_stock=True,
                stock_quantity__gt=models.F('low_stock_threshold')
            )
        elif self.value() == 'low_stock':
            return queryset.filter(
                manage_stock=True,
                stock_quantity__gt=0,
                stock_quantity__lte=models.F('low_stock_threshold')
            )
        elif self.value() == 'out_of_stock':
            return queryset.filter(
                manage_stock=True,
                stock_quantity=0
            )
        return queryset


class PromotionActiveFilter(admin.SimpleListFilter):
    title = _('Status da Promoção')
    parameter_name = 'promotion_status'
    
    def lookups(self, request, model_admin):
        return [
            ('active', _('✅ Ativas agora')),
            ('upcoming', _('🕐 Programadas')),
            ('expired', _('⏹️ Expiradas')),
            ('limit_reached', _('🚫 Limite atingido')),
        ]
    
    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'active':
            return queryset.filter(
                active=True,
                start_date__lte=now,
                end_date__gte=now
            ).exclude(
                Q(usage_limit__isnull=False) & Q(times_used__gte=models.F('usage_limit'))
            )
        elif self.value() == 'upcoming':
            return queryset.filter(
                active=True,
                start_date__gt=now
            )
        elif self.value() == 'expired':
            return queryset.filter(
                end_date__lt=now
            )
        elif self.value() == 'limit_reached':
            return queryset.filter(
                usage_limit__isnull=False,
                times_used__gte=models.F('usage_limit')
            )
        return queryset