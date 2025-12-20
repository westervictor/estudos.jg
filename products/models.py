from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils import timezone
from decimal import Decimal
import uuid


class ProductManager(models.Manager):
    """Manager personalizado para produtos"""
    
    def get_active_products(self):
        """Retorna apenas produtos ativos"""
        return self.filter(active=True, category__active=True)
    
    def get_by_category(self, category_slug):
        """Retorna produtos por categoria"""
        return self.filter(
            category__slug=category_slug,
            active=True
        ).order_by('order', 'name')
    
    def get_featured(self):
        """Retorna produtos em destaque"""
        return self.filter(featured=True, active=True)
    
    def get_promotional(self):
        """Retorna produtos em promoção"""
        return self.filter(has_promotion=True, active=True)


class ProductCategory(models.Model):
    """Categorias de produtos"""
    
    name = models.CharField(
        max_length=50,
        verbose_name='Nome da Categoria'
    )
    
    slug = models.SlugField(
        max_length=60,
        unique=True,
        verbose_name='Slug',
        help_text='Identificador único para URLs'
    )
    
    description = models.TextField(
        verbose_name='Descrição',
        blank=True,
        null=True
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem',
        help_text='Ordem de exibição (menor aparece primeiro)'
    )
    
    active = models.BooleanField(
        default=True,
        verbose_name='Ativa'
    )
    
    show_in_menu = models.BooleanField(
        default=True,
        verbose_name='Mostrar no menu'
    )
    
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Ícone',
        help_text='Código do ícone (ex: fas fa-hamburger)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['slug', 'active']),
            models.Index(fields=['order']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    @property
    def product_count(self):
        """Retorna a quantidade de produtos na categoria"""
        return self.products.count()


class ProductTag(models.Model):
    """Tags para classificação de produtos"""
    
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Nome da Tag'
    )
    
    slug = models.SlugField(
        max_length=60,
        unique=True
    )
    
    color = models.CharField(
        max_length=7,
        default='#007bff',
        verbose_name='Cor da Tag',
        help_text='Cor em hexadecimal (ex: #007bff)'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descrição'
    )
    
    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Modelo principal de produtos"""
    
    STATUS_CHOICES = [
        ('active', 'Ativo'),
        ('inactive', 'Inativo'),
        ('out_of_stock', 'Sem estoque'),
        ('coming_soon', 'Em breve'),
    ]
    
    # Identificação
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='SKU',
        help_text='Código único do produto'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome do Produto'
    )
    
    slug = models.SlugField(
        max_length=110,
        unique=True,
        verbose_name='Slug'
    )
    
    # Categorização
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Categoria'
    )
    
    tags = models.ManyToManyField(
        ProductTag,
        blank=True,
        verbose_name='Tags'
    )
    
    # Informações
    description = models.TextField(
        verbose_name='Descrição Detalhada',
        blank=True,
        null=True
    )
    
    short_description = models.CharField(
        max_length=200,
        verbose_name='Descrição Curta',
        blank=True,
        null=True
    )
    
    # Preços
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço de Custo',
        help_text='Custo de produção/aquisição'
    )
    
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço de Venda'
    )
    
    promotional_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Preço Promocional'
    )
    
    # Status e controle
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Status'
    )
    
    active = models.BooleanField(
        default=True,
        verbose_name='Ativo para venda'
    )
    
    featured = models.BooleanField(
        default=False,
        verbose_name='Destaque'
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem no Menu'
    )
    
    # Estoque
    manage_stock = models.BooleanField(
        default=False,
        verbose_name='Controlar Estoque'
    )
    
    stock_quantity = models.IntegerField(
        default=0,
        verbose_name='Quantidade em Estoque'
    )
    
    low_stock_threshold = models.IntegerField(
        default=0,
        verbose_name='Limite de Estoque Baixo'
    )
    
    # Informações nutricionais
    calories = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Calorias (kcal)'
    )
    
    preparation_time = models.PositiveIntegerField(
        default=15,
        verbose_name='Tempo de Preparo (min)',
        validators=[MinValueValidator(1), MaxValueValidator(120)]
    )
    
    # Imagens
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name='Imagem Principal'
    )
    
    additional_images = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Imagens Adicionais',
        help_text='Lista de URLs de imagens extras'
    )
    
    # Customizações
    allow_customizations = models.BooleanField(
        default=False,
        verbose_name='Permitir Customizações'
    )
    
    max_customizations = models.PositiveIntegerField(
        default=3,
        verbose_name='Máximo de Customizações'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ProductManager()
    
    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'active']),
            models.Index(fields=['featured']),
        ]
    
    def save(self, *args, **kwargs):
        # Gera SKU automático se não fornecido
        if not self.sku:
            prefix = self.category.slug.upper()[:3] if self.category else 'PRO'
            self.sku = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
        
        # Gera slug automático
        if not self.slug:
            self.slug = slugify(self.name)
        
        # Atualiza status baseado no estoque
        if self.manage_stock and self.stock_quantity <= 0:
            self.status = 'out_of_stock'
        
        super().save(*args, **kwargs)
    
    @property
    def current_price(self):
        """Retorna o preço atual (promocional ou normal)"""
        if self.promotional_price and self.promotional_price < self.sale_price:
            return self.promotional_price
        return self.sale_price
    
    @property
    def discount_percentage(self):
        """Calcula percentual de desconto se houver promoção"""
        if self.promotional_price and self.promotional_price < self.sale_price:
            discount = ((self.sale_price - self.promotional_price) / self.sale_price) * 100
            return round(discount, 1)
        return 0
    
    @property
    def has_promotion(self):
        """Verifica se produto está em promoção"""
        return bool(self.promotional_price and self.promotional_price < self.sale_price)
    
    @property
    def profit_margin(self):
        """Calcula margem de lucro"""
        if self.cost_price is not None and self.cost_price > 0:
            return ((self.current_price -
        self.cost_price) / self.cost_price) * 100
        return 0
    
    @property
    def is_available(self):
        """Verifica se produto está disponível para venda"""
        if not self.active:
            return False
        if self.manage_stock and self.stock_quantity <= 0:
            return False
        if self.status not in ['active', 'coming_soon']:
            return False
        return True
    
    @property
    def stock_status(self):
        """Status do estoque"""
        if not self.manage_stock:
            return 'Não controlado'
        if self.stock_quantity <= 0:
            return 'Esgotado'
        if self.stock_quantity <= self.low_stock_threshold:
            return f'Baixo ({self.stock_quantity})'
        return f'Disponível ({self.stock_quantity})'
    
    def reduce_stock(self, quantity=1):
        """Reduz o estoque do produto"""
        if self.manage_stock:
            if self.stock_quantity >= quantity:
                self.stock_quantity -= quantity
                self.save()
                return True
            return False
        return True
    
    def increase_stock(self, quantity=1):
        """Aumenta o estoque do produto"""
        if self.manage_stock:
            self.stock_quantity += quantity
            self.save()
            return True
        return True
    
    def __str__(self):
        return f"{self.name} ({self.sku})"


class ProductCustomizationOption(models.Model):
    """Opções de customização para produtos"""
    
    TYPE_CHOICES = [
        ('checkbox', 'Checkbox (Sim/Não)'),
        ('select', 'Seleção Única'),
        ('multiple', 'Seleção Múltipla'),
        ('number', 'Quantidade'),
    ]
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='customization_options'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome da Opção'
    )
    
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='checkbox'
    )
    
    required = models.BooleanField(
        default=False,
        verbose_name='Obrigatório'
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem'
    )
    
    class Meta:
        verbose_name = 'Opção de Customização'
        verbose_name_plural = 'Opções de Customização'
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductCustomizationChoice(models.Model):
    """Opções de escolha para customizações"""
    
    option = models.ForeignKey(
        ProductCustomizationOption,
        on_delete=models.CASCADE,
        related_name='choices'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome da Escolha'
    )
    
    price_modifier = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Modificador de Preço'
    )
    
    available = models.BooleanField(
        default=True,
        verbose_name='Disponível'
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem'
    )
    
    class Meta:
        verbose_name = 'Escolha de Customização'
        verbose_name_plural = 'Escolhas de Customização'
        ordering = ['order', 'name']
        unique_together = ['option', 'name']
    
    def __str__(self):
        price = f" (+R$ {self.price_modifier})" if self.price_modifier > 0 else ""
        return f"{self.name}{price}"


class Promotion(models.Model):
    """Promoções e descontos"""
    
    TYPE_CHOICES = [
        ('percentage', 'Percentual'),
        ('fixed', 'Valor Fixo'),
        ('bundle', 'Combo'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome da Promoção'
    )
    
    slug = models.SlugField(
        max_length=110,
        unique=True
    )
    
    description = models.TextField(
        verbose_name='Descrição',
        blank=True,
        null=True
    )
    
    promotion_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='percentage',
        verbose_name='Tipo de Promoção'
    )
    
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor do Desconto',
        help_text='Percentual ou valor fixo'
    )
    
    products = models.ManyToManyField(
        Product,
        related_name='promotions',
        blank=True,
        verbose_name='Produtos Incluídos'
    )
    
    categories = models.ManyToManyField(
        ProductCategory,
        related_name='promotions',
        blank=True,
        verbose_name='Categorias Incluídas'
    )
    
    start_date = models.DateTimeField(
        verbose_name='Data de Início'
    )
    
    end_date = models.DateTimeField(
        verbose_name='Data de Término'
    )
    
    active = models.BooleanField(
        default=True,
        verbose_name='Ativa'
    )
    
    priority = models.PositiveIntegerField(
        default=0,
        verbose_name='Prioridade',
        help_text='Promoções com maior prioridade têm precedência'
    )
    
    minimum_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Valor Mínimo do Pedido'
    )
    
    maximum_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Desconto Máximo'
    )
    
    usage_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Limite de Usos'
    )
    
    times_used = models.PositiveIntegerField(
        default=0,
        editable=False,
        verbose_name='Vezes Usada'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Promoção'
        verbose_name_plural = 'Promoções'
        ordering = ['-priority', '-start_date']
        indexes = [
            models.Index(fields=['active', 'start_date', 'end_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Verifica se promoção está ativa no momento"""
        now = timezone.now()
        return (
            self.active and
            self.start_date <= now <= self.end_date and
            (self.usage_limit is None or self.times_used < self.usage_limit)
        )
    
    @property
    def time_remaining(self):
        """Tempo restante para promoção"""
        if not self.is_active:
            return None
        remaining = self.end_date - timezone.now()
        return remaining
    
    def __str__(self):
        status = "✅" if self.is_active else "⏸️"
        return f"{status} {self.name}"


class StockMovement(models.Model):
    """Movimentações de estoque"""
    
    MOVEMENT_TYPES = [
        ('in', 'Entrada'),
        ('out', 'Saída'),
        ('adjustment', 'Ajuste'),
        ('return', 'Devolução'),
    ]
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements'
    )
    
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES
    )
    
    quantity = models.IntegerField(
        verbose_name='Quantidade'
    )
    
    previous_quantity = models.IntegerField(
        verbose_name='Quantidade Anterior'
    )
    
    new_quantity = models.IntegerField(
        verbose_name='Nova Quantidade'
    )
    
    reason = models.CharField(
        max_length=200,
        verbose_name='Motivo',
        blank=True,
        null=True
    )
    
    reference = models.CharField(
        max_length=100,
        verbose_name='Referência',
        blank=True,
        null=True,
        help_text='Número do pedido, nota fiscal, etc.'
    )
    
    created_by = models.CharField(
        max_length=100,
        verbose_name='Registrado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.get_movement_type_display()}: {self.quantity}"

