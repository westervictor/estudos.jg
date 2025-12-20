from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from .models import Product, StockMovement, Promotion


@receiver(pre_save, sender=Product)
def update_product_status(sender, instance, **kwargs):
    """Atualiza status baseado no estoque"""
    if instance.manage_stock:
        if instance.stock_quantity <= 0:
            instance.status = 'out_of_stock'
        elif instance.status == 'out_of_stock' and instance.stock_quantity > 0:
            instance.status = 'active'


@receiver(post_save, sender=StockMovement)
def update_product_stock_from_movement(sender, instance, created, **kwargs):
    """Atualiza estoque do produto quando há movimentação"""
    if created:
        instance.product.stock_quantity = instance.new_quantity
        instance.product.save()


@receiver(m2m_changed, sender=Promotion.products.through)
def update_product_prices_on_promotion_change(sender, instance, action, **kwargs):
    """Atualiza preços promocionais quando produtos são adicionados/removidos"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        for product in instance.products.all():
            if instance.is_active:
                product.promotional_price = instance.apply_discount(product.sale_price)
            else:
                product.promotional_price = None
            product.save()


@receiver(pre_save, sender=Promotion)
def validate_promotion_dates(sender, instance, **kwargs):
    """Valida datas da promoção"""
    if instance.start_date >= instance.end_date:
        raise ValueError("A data de início deve ser anterior à data de término")