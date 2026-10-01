# apps/backend/ecommerce/models/gotomarket.py
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils import timezone
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from invoice.models import Invoice, InvoiceLineItem


class ItemCategory(models.TextChoices):
    """Main categories for Nigerian food items."""
    MEAT = "MEAT", "Meat & Protein"
    POULTRY = "POULTRY", "Poultry"
    FISH = "FISH", "Fish & Seafood"
    VEGETABLE = "VEGETABLE", "Vegetables & Leafy Greens"
    FRUIT = "FRUIT", "Fruits"
    GRAIN = "GRAIN", "Grains & Cereals"
    TUBER = "TUBER", "Tubers & Root Vegetables"
    LEGUME = "LEGUME", "Legumes & Beans"
    SPICE = "SPICE", "Spices & Seasonings"
    OIL = "OIL", "Oils & Fats"
    DAIRY = "DAIRY", "Dairy & Alternatives"
    BEVERAGE = "BEVERAGE", "Beverages"
    SNACK = "SNACK", "Snacks & Pastries"
    CONDIMENT = "CONDIMENT", "Condiments & Sauces"
    OTHER = "OTHER", "Other"


class MarketItem(models.Model):
    """Model for Nigerian food items with comprehensive subcategories."""
    
    # Meat Subcategories
    MEAT_SUBCATEGORIES = [
        ("BEEF", "Beef (Cow Meat)"),
        ("GOAT", "Goat Meat"),
        ("LAMB", "Lamb Meat"),
        ("PORK", "Pork Meat"),
        ("BUSHBUCK", "Bushbuck (Grasscutter)"),
        ("SNAIL", "Snail (Giant African)"),
        ("OFFAL", "Offal (Tripe, Liver, Kidney)"),
        ("BEEF_SUYA", "Beef Suya Cut"),
        ("BEEF_SHANK", "Beef Shank"),
        ("BEEF_RIBS", "Beef Ribs"),
        ("BEEF_TONGUE", "Cow Tongue"),
        ("BEEF_FOOT", "Cow Foot"),
        ("BEEF_HEAD", "Cow Head (Isi Ewu)"),
    ]
    
    # Poultry Subcategories
    POULTRY_SUBCATEGORIES = [
        ("CHICKEN", "Chicken"),
        ("TURKEY", "Turkey"),
        ("DUCK", "Duck"),
        ("GUINEA_FOWL", "Guinea Fowl"),
        ("QUAIL", "Quail"),
        ("EGGS", "Eggs"),
        ("CHICKEN_PARTS", "Chicken Parts (Breast, Thigh, Wings)"),
        ("FROZEN_CHICKEN", "Frozen Chicken"),
    ]
    
    # Fish & Seafood Subcategories
    FISH_SUBCATEGORIES = [
        ("TILAPIA", "Tilapia"),
        ("CATFISH", "Catfish"),
        ("MACKEREL", "Mackerel (Titus)"),
        ("SARDINE", "Sardine"),
        ("TUNA", "Tuna"),
        ("PANGASIUS", "Pangasius (Pangas)"),
        ("STOCKFISH", "Stockfish"),
        ("SMOKED_FISH", "Smoked Fish"),
        ("DRIED_FISH", "Dried Fish (Eja Kika)"),
        ("SHRIMP", "Shrimp/Prawns"),
        ("CRAYFISH", "Crayfish (Dried)"),
        ("PERIWINKLE", "Periwinkle"),
        ("OCTOPUS", "Octopus"),
        ("FISH_ROE", "Fish Roe (Eja Nla)"),
    ]
    
    # Vegetable & Leafy Green Subcategories
    VEGETABLE_SUBCATEGORIES = [
        ("UGU", "Ugu (Pumpkin Leaves)"),
        ("WATERLEAF", "Waterleaf (Gbure)"),
        ("SPINACH", "Spinach"),
        ("BITTER_LEAF", "Bitter Leaf (Onugbu)"),
        ("EWEDU", "Ewedu (Jute Leaves)"),
        ("OKRA", "Okro (Ila)"),
        ("GREEN", "Green Leafy Vegetables"),
        ("CABBAGE", "Cabbage"),
        ("LETTUCE", "Lettuce"),
        ("TOMATO", "Tomatoes"),
        ("PEPPER", "Peppers (Bell, Chili)"),
        ("ONION", "Onions"),
        ("GARLIC", "Garlic"),
        ("GINGER", "Ginger"),
        ("CUCUMBER", "Cucumber"),
        ("CARROT", "Carrots"),
        ("BROCCOLI", "Broccoli"),
        ("CAULIFLOWER", "Cauliflower"),
        ("MUSHROOM", "Mushrooms"),
        ("SPRING_ONION", "Spring Onions (Alubosa elewe)"),
        ("EFO_RIRI", "Efo Riri (Nigerian Spinach)"),
    ]
    
    # Fruit Subcategories
    FRUIT_SUBCATEGORIES = [
        ("ORANGE", "Oranges"),
        ("BANANA", "Bananas"),
        ("PLANTAIN", "Plantain (Ogede)"),
        ("PINEAPPLE", "Pineapples"),
        ("MANGO", "Mangoes"),
        ("AVOCADO", "Avocado (Ube oyibo)"),
        ("PAPAYA", "Papaya (Ibepe)"),
        ("WATERMELON", "Watermelon"),
        ("GUAVA", "Guava (Guro)"),
        ("APPLE", "Apples"),
        ("GRAPE", "Grapes"),
        ("CASHEW", "Cashew Fruit (Kaju)"),
        ("TIGER_NUT", "Tiger Nut (Aya)"),
        ("PAWPAW", "Pawpaw"),
        ("LEMON", "Lemon"),
        ("LIME", "Lime"),
        ("UCHU", "Uchu (Aidan Fruit)"),
        ("FRESH_DATES", "Fresh Dates"),
    ]
    
    # Grain & Cereal Subcategories
    GRAIN_SUBCATEGORIES = [
        ("RICE", "Rice (Local & Imported)"),
        ("OFADA_RICE", "Ofada Rice"),
        ("ABAKALIKI_RICE", "Abakaliki Rice"),
        ("BASMATI", "Basmati Rice"),
        ("MAIZE", "Maize (Corn)"),
        ("MILLET", "Millet (Gero)"),
        ("SORGHUM", "Sorghum (Oka baba)"),
        ("WHEAT", "Wheat"),
        ("BARLEY", "Barley"),
        ("OATS", "Oats"),
        ("CORN_FLOUR", "Corn Flour (Pap)"),
        ("GARRI", "Garri (Cassava Flour)"),
        ("SEMOLINA", "Semolina"),
        ("FUFU_FLOUR", "Fufu Flour"),
        ("AMALA_FLOUR", "Amala Flour"),
        ("LAFUN_FLOUR", "Lafun Flour"),
        ("WHEAT_FLOUR", "Wheat Flour"),
        ("BREAD_FLOUR", "Bread Flour"),
        ("PASTA", "Pasta (Spaghetti, Macaroni)"),
        ("NOODLES", "Noodles (Indomie)"),
    ]
    
    # Tuber & Root Vegetable Subcategories
    TUBER_SUBCATEGORIES = [
        ("YAM", "Yam (Isu)"),
        ("WHITE_YAM", "White Yam"),
        ("WATER_YAM", "Water Yam"),
        ("CASSAVA", "Cassava"),
        ("SWEET_POTATO", "Sweet Potato (Anamo)"),
        ("COCOYAM", "Cocoyam"),
        ("COCOYAM_LEAVES", "Cocoyam Leaves (Ede)"),
        ("PLANTAIN_GREEN", "Green Plantain"),
        ("PLANTAIN_RIPE", "Ripe Plantain"),
        ("POTATO", "Irish Potato"),
        ("BAMBOO_SHOOT", "Bamboo Shoot"),
    ]
    
    # Legume & Bean Subcategories
    LEGUME_SUBCATEGORIES = [
        ("BEANS", "Beans (Ewa)"),
        ("COWPEA", "Cowpea (Black-eyed Peas)"),
        ("HONEY_BEANS", "Honey Beans (Ewa oloyin)"),
        ("KIDNEY_BEANS", "Kidney Beans"),
        ("LIMA_BEANS", "Lima Beans (Butter Beans)"),
        ("PEAS", "Green Peas"),
        ("PIGEON_PEA", "Pigeon Pea (Fio-fio)"),
        ("GROUNDNUT", "Groundnuts (Peanuts)"),
        ("SOYBEAN", "Soybeans"),
        ("MOI_MOI_MIX", "Moi Moi Mix"),
        ("AKARA_MIX", "Akara Mix"),
    ]
    
    # Spice & Seasoning Subcategories
    SPICE_SUBCATEGORIES = [
        ("PEPPER", "Pepper (Ata)"),
        ("ATA_RODO", "Ata Rodo (Scotch Bonnet)"),
        ("TATASHE", "Tatashe (Bell Pepper)"),
        ("SHOMBO", "Shombo (Dried Pepper)"),
        ("ONION", "Onion Powder"),
        ("GARLIC", "Garlic Powder"),
        ("GINGER", "Ginger Powder"),
        ("THYME", "Thyme"),
        ("CURRY", "Curry Powder"),
        ("NUTMEG", "Nutmeg (Ehuru)"),
        ("CLOVE", "Cloves (Kanafuru)"),
        ("CINNAMON", "Cinnamon"),
        ("ALLSPICE", "Allspice"),
        ("PAPRIKA", "Paprika"),
        ("CUMIN", "Cumin"),
        ("CORIANDER", "Coriander"),
        ("BAY_LEAVES", "Bay Leaves"),
        ("SAVORY", "Savory"),
        ("STOCK_CUBE", "Stock Cubes (Knorr, Maggi)"),
        ("SUYA_SPICE", "Suya Spice Mix"),
        ("DAWADAWA", "Dawadawa (Locust Bean)"),
        ("IRU", "Iru (Fermented Locust Bean)"),
    ]
    
    # Oil & Fat Subcategories
    OIL_SUBCATEGORIES = [
        ("PALM_OIL", "Palm Oil (Epo pupa)"),
        ("VEGETABLE_OIL", "Vegetable Oil"),
        ("OLIVE_OIL", "Olive Oil"),
        ("COCONUT_OIL", "Coconut Oil"),
        ("GROUNDNUT_OIL", "Groundnut Oil"),
        ("SESAME_OIL", "Sesame Oil"),
        ("BUTTER", "Butter"),
        ("MARGARINE", "Margarine"),
        ("SHEA_BUTTER", "Shea Butter"),
    ]
    
    # Dairy & Alternatives Subcategories
    DAIRY_SUBCATEGORIES = [
        ("MILK", "Milk"),
        ("POWDERED_MILK", "Powdered Milk (Peak, Nido)"),
        ("EVAPORATED_MILK", "Evaporated Milk"),
        ("YOGURT", "Yogurt"),
        ("CHEESE", "Cheese"),
        ("WARA", "Wara (Local Cheese)"),
        ("EGGS", "Eggs"),
        ("ICE_CREAM", "Ice Cream"),
        ("BUTTERMILK", "Buttermilk"),
    ]
    
    # Beverage Subcategories
    BEVERAGE_SUBCATEGORIES = [
        ("TEA", "Tea (Black, Green, Herbal)"),
        ("COFFEE", "Coffee"),
        ("CHOCOLATE", "Chocolate Drink (Milo, Bournvita)"),
        ("ZOBE", "Zobo (Hibiscus Drink)"),
        ("PALM_WINE", "Palm Wine (Emu)"),
        ("KUNU", "Kunu (Millet/Guinea Corn Drink)"),
        ("FURA", "Fura (Fermented Milk Drink)"),
        ("SOBO", "Sobo (Sorrel Drink)"),
        ("GINGER_DRINK", "Ginger Drink"),
        ("LEMON_DRINK", "Lemon Drink"),
        ("FRESH_JUICE", "Fresh Fruit Juice"),
        ("COCONUT_WATER", "Coconut Water"),
    ]
    
    # Snack & Pastry Subcategories
    SNACK_SUBCATEGORIES = [
        ("BREAD", "Bread"),
        ("AGELE", "Agele (Fermented Cassava Cake)"),
        ("AKARA", "Akara (Bean Cake)"),
        ("MOI_MOI", "Moi Moi (Steamed Bean Pudding)"),
        ("MEAT_PIE", "Meat Pie"),
        ("SCOTCH_EGG", "Scotch Egg"),
        ("SAMOSA", "Samosa"),
        ("SPRING_ROLL", "Spring Roll"),
        ("DONUT", "Donut (Puff Puff)"),
        ("BUNS", "Buns"),
        ("CHIN_CHIN", "Chin Chin"),
        ("EGGO", "Eggo (Chin Chin Variation)"),
        ("KOOSE", "Koose (Bean Cake)"),
        ("KULIKULI", "Kulikuli (Peanut Cake)"),
        ("PANKASU", "Pankasu (Peanut Brittle)"),
        ("CASSAVA_CHIPS", "Cassava Chips"),
        ("PLANTAIN_CHIPS", "Plantain Chips"),
        ("COCONUT_BALLS", "Coconut Balls"),
        ("GROUNDNUT_BALLS", "Groundnut Balls (Tiger Nut)"),
    ]
    
    # Condiment & Sauce Subcategories
    CONDIMENT_SUBCATEGORIES = [
        ("TOMATO_PASTE", "Tomato Paste"),
        ("PEPPER_PASTE", "Pepper Paste (Tatashe, Ata Rodo)"),
        ("PEPPER_SAUCE", "Pepper Sauce"),
        ("OYO", "Oyo (Fermented Oil Palm Fruit)"),
        ("DAWADAWA", "Dawadawa (Locust Bean)"),
        ("IRU", "Iru (Fermented Locust Bean)"),
        ("OGIRI", "Ogiri (Fermented Melon)"),
        ("OGBONO", "Ogbono (African Mango Seeds)"),
        ("EGUSI", "Egusi (Melon Seeds)"),
        ("PALM_NUT", "Palm Nut (Igi ope)"),
        ("BANGA_NUT", "Banga Nut"),
        ("SOY_SAUCE", "Soy Sauce"),
        ("VINEGAR", "Vinegar"),
        ("KETCHUP", "Ketchup"),
        ("MAYONNAISE", "Mayonnaise"),
    ]
    
    # ALL_SUBCATEGORIES combines all subcategories for validation
    ALL_SUBCATEGORIES = (
        MEAT_SUBCATEGORIES + POULTRY_SUBCATEGORIES + FISH_SUBCATEGORIES +
        VEGETABLE_SUBCATEGORIES + FRUIT_SUBCATEGORIES + GRAIN_SUBCATEGORIES +
        TUBER_SUBCATEGORIES + LEGUME_SUBCATEGORIES + SPICE_SUBCATEGORIES +
        OIL_SUBCATEGORIES + DAIRY_SUBCATEGORIES + BEVERAGE_SUBCATEGORIES +
        SNACK_SUBCATEGORIES + CONDIMENT_SUBCATEGORIES
    )
    
    # Model Fields
    name = models.CharField(max_length=200, help_text="Name of the food item")
    category = models.CharField(max_length=20, choices=ItemCategory.choices, db_index=True)
    subcategory = models.CharField(
        max_length=50,
        choices=ALL_SUBCATEGORIES,
        blank=True,
        null=True,
        db_index=True,
        help_text="Specific food subcategory"
    )
    description = models.TextField(blank=True, help_text="Description of the item")
    
    # Pricing and Stock
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    
    # Unit of measurement
    UNIT_CHOICES = [
        ("KG", "Kilogram"),
        ("G", "Gram"),
        ("L", "Liter"),
        ("ML", "Milliliter"),
        ("UNIT", "Unit"),
        ("BUNCH", "Bunch"),
        ("PIECE", "Piece"),
        ("BAG", "Bag"),
        ("CUP", "Cup"),
        ("TABLESPOON", "Tablespoon"),
        ("TEASPOON", "Teaspoon"),
    ]
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="KG")
    
    # Amazon-level inventory management
    quantity_on_hand = models.PositiveIntegerField(default=0)
    quantity_committed = models.PositiveIntegerField(default=0)
    restock_threshold = models.PositiveIntegerField(default=10)
    lead_time_days = models.PositiveIntegerField(default=3)
    
    # Supplier information
    supplier = models.CharField(max_length=200, blank=True)
    supplier_contact = models.CharField(max_length=100, blank=True)
    
    # Images
    image = models.ImageField(upload_to='market_items/', blank=True, null=True)
    
    # Seasonal availability
    is_seasonal = models.BooleanField(default=False)
    season_start = models.DateField(blank=True, null=True)
    season_end = models.DateField(blank=True, null=True)
    
    # Organic certification
    is_organic = models.BooleanField(default=False)
    is_locally_sourced = models.BooleanField(default=True)
    origin_region = models.CharField(max_length=100, blank=True, help_text="Region of origin in Nigeria")
    
    # Status
    is_available = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_market_items"
    )

    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'subcategory']),
            models.Index(fields=['is_available', 'is_featured']),
            models.Index(fields=['quantity_on_hand', 'restock_threshold']),
            models.Index(fields=['name']),
        ]
        verbose_name = "Market Item"
        verbose_name_plural = "Market Items"

    def __str__(self):
        subcat = f" - {self.get_subcategory_display()}" if self.subcategory else ""
        return f"{self.name} ({self.get_category_display()}{subcat})"

    @property
    def is_in_stock(self):
        """Returns True if item is in stock."""
        return self.stock > 0

    @property
    def is_low_stock(self):
        """Returns True if stock is below threshold."""
        return self.quantity_on_hand <= self.restock_threshold

    @property
    def is_out_of_stock(self):
        """Returns True if item is out of stock."""
        return self.quantity_on_hand <= 0
    
    @property
    def quantity_available(self):
        """Calculate available quantity."""
        return max(0, self.quantity_on_hand - self.quantity_committed)
    
    # Add this for annotating in queries if needed
    @classmethod
    def annotate_quantity_available(cls, queryset):
        """Annotate queryset with quantity_available."""
        return queryset.annotate(
            quantity_available=models.F('quantity_on_hand') - models.F('quantity_committed')
        )


class Purchase(models.Model):
    """Purchase model using centralized Invoice system."""
    
    PURCHASE_STATUS = [
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purchases"
    )
    purchase_number = models.CharField(
        max_length=32,
        unique=True,
        editable=False
    )
    status = models.CharField(
        max_length=20,
        choices=PURCHASE_STATUS,
        default='DRAFT'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Reference to centralized invoice
    invoice = models.OneToOneField(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase",
        help_text="Centralized invoice for this purchase"
    )
    
    # Persisted financials
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    vat_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=Decimal(str(getattr(settings, "DEFAULT_VAT_RATE", 0.075)))
    )
    vat_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal(str(getattr(settings, "DEFAULT_DISCOUNT", 0.00)))
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    
    # Delivery information
    delivery_address = models.TextField(blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    delivery_instructions = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        """Override save to generate purchase number and create invoice."""
        if not self.purchase_number:
            year, num = self._get_next_counter()
            self.purchase_number = f"INV-{year}-{num:04d}"
        
        # Calculate totals
        self.calculate_totals()
        
        super().save(*args, **kwargs)
        
        # Create or update invoice after purchase is saved
        self._sync_with_invoice()

    def _get_next_counter(self):
        """Get next counter for purchase number."""
        year = timezone.now().year
        with transaction.atomic():
            obj, created = PurchaseCounter.objects.select_for_update().get_or_create(year=year)
            obj.counter += 1
            obj.save(update_fields=["counter"])
            return year, obj.counter

    def calculate_totals(self):
        """Calculate all financial totals."""
        self.subtotal = sum(item.line_total for item in self.items.all())
        self.vat_amount = (self.subtotal * self.vat_rate).quantize(Decimal("0.01"))
        self.total = self.subtotal + self.vat_amount - self.discount

    def _sync_with_invoice(self):
        """Create or update the centralized invoice."""
        if not self.invoice:
            # Create new invoice
            invoice = Invoice.objects.create(
                customer=self.user,
                number=self.purchase_number,
                invoice_number=self.purchase_number,
                issue_date=timezone.now().date(),
                created=timezone.now(),
                subtotal=self.subtotal,
                tax_amount=self.vat_amount,
                discount_amount=self.discount,
                total_amount=self.total,
                amount_paid=Decimal('0.00') if self.status != 'PAID' else self.total,
                balance_due=self.total if self.status != 'PAID' else Decimal('0.00'),
                currency='NGN',
                status=self._map_status_to_invoice_status(),
                billing_name=self.user.get_full_name() or self.user.email,
                billing_email=self.user.email,
                billing_address=self.delivery_address if self.delivery_address else "",
                notes=f"Purchase from GoToMarket",
                created_by=self.user,
            )
            self.invoice = invoice
            self.save(update_fields=['invoice'])
            
            # Create invoice line items
            for item in self.items.all():
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=item.product_name,
                    sku=f"GTM-{item.product_name[:10]}",
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=item.line_total,
                    tax=Decimal('0.00'),  # VAT is applied at invoice level
                )
        else:
            # Update existing invoice
            invoice = self.invoice
            invoice.subtotal = self.subtotal
            invoice.tax_amount = self.vat_amount
            invoice.discount_amount = self.discount
            invoice.total_amount = self.total
            invoice.balance_due = self.total - invoice.amount_paid
            invoice.status = self._map_status_to_invoice_status()
            invoice.save()

    def _map_status_to_invoice_status(self):
        """Map purchase status to invoice status."""
        status_map = {
            'DRAFT': 'DRAFT',
            'CONFIRMED': 'SENT',
            'PAID': 'PAID',
            'CANCELLED': 'CANCELLED',
            'REFUNDED': 'REFUNDED',
        }
        return status_map.get(self.status, 'DRAFT')

    @property
    def receipt_html(self):
        """Generate HTML receipt using centralized invoice."""
        if not self.invoice:
            return "<p>No invoice available</p>"
        
        seller_name = getattr(settings, "MARKET_NAME", "GoToMarket")
        seller_logo = getattr(settings, "MARKET_LOGO_URL", "")
        seller_addr = getattr(settings, "MARKET_ADDRESS", "")
        seller_phone = getattr(settings, "MARKET_PHONE", "")

        rows = ""
        for line in self.invoice.line_items.all():
            rows += f"""
            <tr>
              <td style="padding:6px">{line.description}</td>
              <td style="text-align:center">{line.quantity}</td>
              <td style="text-align:right">â‚¦{line.unit_price:.2f}</td>
              <td style="text-align:right">â‚¦{line.total:.2f}</td>
            </tr>
            """

        html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"/>
<style>
  body {{ font-family: Arial, sans-serif; max-width:420px; margin:0 auto; padding:12px; color:#111; }}
  .header {{ text-align:center; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
  th, td {{ border-bottom:1px solid #eee; padding:6px; }}
  .total-row td {{ border-top:1px solid #000; font-weight:bold; }}
  .status-badge {{ display:inline-block; padding:2px 8px; border-radius:3px; font-size:12px; font-weight:bold; }}
  .status-PAID {{ background-color:#4CAF50; color:white; }}
  .status-SENT {{ background-color:#2196F3; color:white; }}
  .status-DRAFT {{ background-color:#9E9E9E; color:white; }}
  .status-CANCELLED {{ background-color:#f44336; color:white; }}
  .status-REFUNDED {{ background-color:#9C27B0; color:white; }}
  .status-OVERDUE {{ background-color:#FF9800; color:white; }}
  .status-VOID {{ background-color:#607D8B; color:white; }}
</style>
</head>
<body>
  <div class="header">
    {f"<img src='{seller_logo}' alt='logo' style='max-height:80px;margin-bottom:6px' />" if seller_logo else ""}
    <h2 style="margin:4px 0">{seller_name}</h2>
    <div style="font-size:12px">{seller_addr}<br/>Tel: {seller_phone}</div>
  </div>

  <div style="margin-top:10px;font-size:13px">
    <div><strong>Invoice:</strong> {self.invoice.number}</div>
    <div><strong>Date:</strong> {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}</div>
    <div><strong>Status:</strong> 
      <span class="status-badge status-{self.invoice.status}">
        {self.invoice.get_status_display()}
      </span>
    </div>
  </div>

  <table>
    <thead>
      <tr><th style="text-align:left">Item</th><th style="text-align:center">Qty</th><th style="text-align:right">Price</th><th style="text-align:right">Total</th></tr>
    </thead>
    <tbody>
      {rows}
      <tr class="total-row">
        <td colspan="3" style="text-align:right">Subtotal</td>
        <td style="text-align:right">â‚¦{self.subtotal:.2f}</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:right">VAT ({float(self.vat_rate)*100:.1f}%)</td>
        <td style="text-align:right">â‚¦{self.vat_amount:.2f}</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:right">Discount</td>
        <td style="text-align:right">-â‚¦{self.discount:.2f}</td>
      </tr>
      <tr class="total-row">
        <td colspan="3" style="text-align:right">Grand Total</td>
        <td style="text-align:right">â‚¦{self.total:.2f}</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:right">Amount Paid</td>
        <td style="text-align:right">â‚¦{self.invoice.amount_paid:.2f}</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:right">Balance Due</td>
        <td style="text-align:right">â‚¦{self.invoice.balance_due:.2f}</td>
      </tr>
    </tbody>
  </table>

  {f"<div style='margin-top:8px;font-size:12px'><strong>Delivery:</strong> {self.delivery_address}<br/><strong>Instructions:</strong> {self.delivery_instructions}</div>" if self.delivery_address else ""}

  <div style="text-align:center; margin-top:12px; font-size:12px;">
    Thank you for shopping with us!<br/>
    <em>Your satisfaction is our priority</em>
  </div>
</body>
</html>"""
        return html

    @property
    def receipt_text(self):
        """Generate text receipt."""
        parts = [
            getattr(settings, "MARKET_NAME", "GoToMarket"),
            getattr(settings, "MARKET_ADDRESS", ""),
            f"Tel: {getattr(settings, 'MARKET_PHONE', '')}",
            "",
            f"Invoice: {self.purchase_number}",
            f"Date: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Status: {self.get_status_display()}",
            "",
        ]
        
        for line in self.items.all():
            parts.append(
                f"{line.product_name} x{line.quantity} @ â‚¦{line.unit_price:.2f} = â‚¦{line.line_total:.2f}"
            )
        
        parts += [
            "",
            f"Subtotal: â‚¦{self.subtotal:.2f}",
            f"VAT: â‚¦{self.vat_amount:.2f}",
            f"Discount: -â‚¦{self.discount:.2f}",
            f"Grand Total: â‚¦{self.total:.2f}",
            f"Amount Paid: â‚¦{self.invoice.amount_paid:.2f}" if self.invoice else "",
            f"Balance Due: â‚¦{self.invoice.balance_due:.2f}" if self.invoice else "",
            "",
            "Thank you for shopping!",
            "Your satisfaction is our priority"
        ]
        return "\n".join(parts)

    def generate_pdf_bytes(self):
        """Generate PDF bytes using weasyprint."""
        try:
            from weasyprint import HTML
            return HTML(string=self.receipt_html, base_url="").write_pdf()
        except ImportError:
            # Fallback: return None if weasyprint is not installed
            return None

    def mark_as_paid(self, payment_method='', payment_reference='', verified_by=None):
        """Mark purchase as paid and update invoice."""
        self.status = 'PAID'
        self.save()
        
        if self.invoice:
            self.invoice.mark_as_paid(
                payment_method=payment_method,
                payment_reference=payment_reference,
                verified_by=verified_by
            )

    def mark_as_confirmed(self):
        """Mark purchase as confirmed."""
        self.status = 'CONFIRMED'
        self.save()
        
        if self.invoice:
            self.invoice.mark_as_sent(sent_by=self.user)

    def cancel_purchase(self, reason='', cancelled_by=None):
        """Cancel the purchase."""
        self.status = 'CANCELLED'
        self.save()
        
        if self.invoice:
            self.invoice.cancel_invoice(
                reason=reason,
                cancelled_by=cancelled_by
            )

    def refund_purchase(self, amount=None):
        """Refund the purchase."""
        self.status = 'REFUNDED'
        self.save()
        
        if self.invoice:
            # Create refund payment
            from invoice.models import InvoicePayment
            InvoicePayment.objects.create(
                invoice=self.invoice,
                amount=amount or self.total,
                payment_method='REFUND',
                payment_reference=f"REFUND-{self.purchase_number}",
                status='REFUNDED',
                created_by=self.user,
            )
            self.invoice.status = 'REFUNDED'
            self.invoice.save()


class PurchaseCounter(models.Model):
    """Counter for generating unique purchase numbers."""
    year = models.IntegerField(unique=True)
    counter = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Purchase Counter"
        verbose_name_plural = "Purchase Counters"


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(
        Purchase,
        related_name="items",
        on_delete=models.CASCADE
    )
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Optional reference to the original market item
    market_item = models.ForeignKey(
        MarketItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_items"
    )

    def save(self, *args, **kwargs):
        self.line_total = (Decimal(self.quantity) * Decimal(self.unit_price)).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
        # Update purchase totals after saving line item
        self.purchase.calculate_totals()
        self.purchase.save()

    def __str__(self):
        return f"{self.product_name} x{self.quantity} = â‚¦{self.line_total}"

