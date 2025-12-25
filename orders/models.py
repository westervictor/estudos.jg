from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import uuid
from products.models import Product

class OrderManager(models.Manager):
    """Manager personalizado para operações de pedido"""
    
    def get_orders_by_status(self, status):
        """Retorna pedidos por status"""
        return self.filter(status=status).order_by('-created_at')
    
    def get_todays_orders(self):
        """Retorna pedidos do dia atual"""
        today = timezone.now().date()
        return self.filter(
            created_at__date=today
        ).order_by('-created_at')
    
    def get_active_orders(self):
        """Retorna pedidos que ainda não foram entregues"""
        return self.exclude(status='delivered').order_by('-created_at')

class Order(models.Model):
    """Modelo principal de pedidos"""
    
    STATUS_CHOICES = [
        ('open', '🟡 Aberto'),
        ('preparing', '👨‍🍳 Em preparo'),
        ('ready', '✅ Pronto para entrega'),
        ('out_for_delivery', '🚗 Saiu para entrega'),
        ('delivered', '📦 Entregue'),
        ('cancelled', '❌ Cancelado'),
    ]
    
    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('urgent', 'Urgente'),
        ('priority', 'Prioritário'),
    ]
    
    VALID_TRANSITIONS = {
        'open': ['preparing', 'cancelled'],
        'preparing': ['ready', 'cancelled'],
        'ready': ['out_for_delivery', 'delivered'],
        'out_for_delivery': ['delivered'],
        'delivered': [],
        'cancelled': [],
    }
    
    # Campos principais
    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='Número do Pedido'
    )
    
    customer_name = models.CharField(
        max_length=100,
        verbose_name='Nome do Cliente',
        blank=True,
        null=True
    )
    
    customer_phone = models.CharField(
        max_length=20,
        verbose_name='Telefone',
        blank=True,
        null=True
    )
    
    delivery_address = models.TextField(
        verbose_name='Endereço de Entrega',
        blank=True,
        null=True
    )
    
    is_delivery = models.BooleanField(
        default=False,
        verbose_name='É entrega?'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name='Status'
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name='Prioridade'
    )
    
    notes = models.TextField(
        verbose_name='Observações',
        blank=True,
        null=True
    )
    
    estimated_time = models.PositiveIntegerField(
        verbose_name='Tempo Estimado (min)',
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(180)]
    )
    
    # Campos de data/hora
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    prepared_at = models.DateTimeField(blank=True, null=True, verbose_name='Preparado em')
    delivered_at = models.DateTimeField(blank=True, null=True, verbose_name='Entregue em')
    
    # Campos financeiros
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Subtotal'
    )
    
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Taxa de Entrega'
    )
    
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),  # ❌ Altere 0.00 para isto
        verbose_name='Desconto'
   )
    
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Impostos'
    )
    
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Total'
    )
    
    # Métodos de pagamento
    PAYMENT_CHOICES = [
        ('cash', 'Dinheiro'),
        ('credit_card', 'Cartão de Crédito'),
        ('debit_card', 'Cartão de Débito'),
        ('pix', 'PIX'),
        ('online', 'Online'),
    ]
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default='cash',
        verbose_name='Método de Pagamento'
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pendente'),
            ('paid', 'Pago'),
            ('refunded', 'Reembolsado'),
        ],
        default='pending',
        verbose_name='Status do Pagamento'
    )
    
    objects = OrderManager()
    
    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['order_number']),
            models.Index(fields=['customer_phone']),
        ]
    
    def save(self, *args, **kwargs):
        """Sobrescreve save para gerar número do pedido e calcular total"""
        if not self.order_number:
            # Gera número sequencial do dia: PD-YYYYMMDD-001
            today = timezone.now().date()
            date_str = today.strftime('%Y%m%d')
            last_order = Order.objects.filter(
                created_at__date=today
            ).order_by('created_at').last()
            
            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.order_number = f"PD-{date_str}-{new_number:03d}"
        
        # Atualiza timestamps de status antes de salvar
        if self.status == 'preparing' and not self.prepared_at:
            self.prepared_at = timezone.now()
        elif self.status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        
        # Salva primeiro para ter PK (necessário para acessar items)
        super().save(*args, **kwargs)
        
        # Calcula totais apenas se já tiver PK (pode acessar items)
        if self.pk:
            # Recalcula totais baseado nos itens
            self.calculate_totals()
            # Atualiza os campos calculados sem chamar save() novamente (evita loop)
            Order.objects.filter(pk=self.pk).update(
                subtotal=self.subtotal,
                delivery_fee=self.delivery_fee,
                tax=self.tax,
                total=self.total,
                prepared_at=self.prepared_at,
                delivered_at=self.delivered_at
            )
            # Atualiza os atributos do objeto em memória
            self.refresh_from_db()
    
    def calculate_totals(self):
        """Calcula todos os valores do pedido"""
        items_total = sum(
            (item.subtotal for item in self.items.all()),
             Decimal('0.00') 
        )
        self.subtotal = items_total
        
        # Se for delivery, adiciona taxa
        if self.is_delivery and self.delivery_fee == Decimal('0.00'):
            # Taxa padrão de entrega (pode ser configurável)
            self.delivery_fee = Decimal('5.00')
        
        # Calcula impostos (10% exemplo)
        self.delivery_fee = Decimal(self.delivery_fee)
        self.tax = (self.subtotal + self.delivery_fee) * Decimal('0.10')
        
        # Calcula total final
        
        self.total = self.subtotal + self.delivery_fee + self.tax - self.discount
    
    @property
    def total_amount(self):
        """Propriedade para compatibilidade"""
        return self.total
    
    @property
    def item_count(self):
        """Quantidade total de itens no pedido"""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
    
    @property
    def preparation_time(self):
        """Tempo decorrido desde a criação do pedido"""
        if not self.prepared_at:
            return None
        return (self.prepared_at - self.created_at).seconds // 60
    
    @property
    def is_active(self):
        """Verifica se pedido está ativo"""
        return self.status not in ['delivered', 'cancelled']
    
    def change_status(self, new_status, user=None):
        """Método seguro para mudança de status"""
        if new_status == self.status:
            return True
        
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(
                f'Transição inválida de {self.get_status_display()} '
                f'para {dict(self.STATUS_CHOICES).get(new_status)}'
            )
        
        if new_status != 'cancelled' and not self.can_change_status():
            raise ValidationError(
                'Não é possível alterar status: pedido está vazio'
            )
        
        # Log da alteração
        if user:
            OrderStatusHistory.objects.create(
                order=self,
                old_status=self.status,
                new_status=new_status,
                changed_by=user
            )
        
        self.status = new_status
        self.save()
        return True
    
    def can_change_status(self):
        """Verifica se pode mudar status"""
        return self.items.exists()
    
    def add_item(self, product, quantity=1, customizations=None):
        """Adiciona item ao pedido"""
        item = OrderItem.objects.create(
            order=self,
            product=product,
            quantity=quantity,
            unit_price=product.current_price
        )
        
        if customizations:
            for customization in customizations:
                item.customizations.create(
                    option=customization['option'],
                    choice=customization['choice'],
                    extra_price=customization.get('extra_price', 0)
                )
        
        self.calculate_totals()
        self.save()
        return item
    
    def clean(self):
        """Validações do modelo"""
        if self.is_delivery and not self.delivery_address:
            raise ValidationError({
                'delivery_address': 'Endereço é obrigatório para entregas'
            })
        
        if self.discount > self.subtotal + self.delivery_fee:
            raise ValidationError({
                'discount': 'Desconto não pode ser maior que o valor total'
            })
    
    def __str__(self):
        return f'{self.order_number} - {self.get_status_display()}'


class OrderItem(models.Model):
    """Itens do pedido com opções de customização"""
    
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name='Pedido'
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Produto'
    )
    
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name='Quantidade'
    )
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço Unitário'
    )
    
    special_instructions = models.TextField(
        verbose_name='Instruções Especiais',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        ordering = ['created_at']
    
    @property
    def subtotal(self):
        """Calcula subtotal do item com customizações"""
        if self.unit_price is None or self.quantity is None:
            return Decimal('0.00')
        
        base_price = self.unit_price * self.quantity
        
        # Adiciona preços das customizações
        extras = self.customizations.aggregate(
            total=models.Sum('extra_price')
        )['total'] or Decimal('0.00')
        
        return base_price + (extras * self.quantity)
    
    @property
    def description_with_extras(self):
        """Descrição completa do item com customizações"""
        description = f"{self.quantity}x {self.product.name}"
        
        if self.customizations.exists():
            extras = [c.description for c in self.customizations.all()]
            description += f" ({', '.join(extras)})"
        
        if self.special_instructions:
            description += f" [Instrução: {self.special_instructions}]"
        
        return description
    
    def save(self, *args, **kwargs):
        """Garante que unit_price seja preenchido com preço do produto"""
        if not self.unit_price and self.product:
            self.unit_price = self.product.current_price
        
        super().save(*args, **kwargs)
        self.order.calculate_totals()
        self.order.save()
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


class OrderItemCustomization(models.Model):
    """Customizações dos itens do pedido (ex: sem cebola, bacon extra)"""
    
    item = models.ForeignKey(
        OrderItem,
        related_name='customizations',
        on_delete=models.CASCADE
    )
    
    option = models.CharField(max_length=50, verbose_name='Opção')
    choice = models.CharField(max_length=50, verbose_name='Escolha')
    extra_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Preço Extra'
    )
    
    class Meta:
        verbose_name = 'Customização'
        verbose_name_plural = 'Customizações'
    
    @property
    def description(self):
        return f"{self.option}: {self.choice}"
    
    def __str__(self):
        return self.description


class OrderStatusHistory(models.Model):
    """Histórico de alterações de status do pedido"""
    
    order = models.ForeignKey(
        Order,
        related_name='status_history',
        on_delete=models.CASCADE
    )
    
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.CharField(max_length=100)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Histórico de Status'
        verbose_name_plural = 'Históricos de Status'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} → {self.new_status}"