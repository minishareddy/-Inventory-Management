from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("staff", "Staff"),
        ("manager", "Manager"),
    ]
    image = models.ImageField(
        upload_to="Users/", default="Users/default.png", blank=True, null=True
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="staff")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class Notification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    status = models.CharField(
        max_length=50,
        choices=[("unread", "Unread"), ("read", "Read")],
        default="unread",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}"


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.category_name


class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    supplier_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    supplier_logo = models.ImageField(
        upload_to="supplier_logos/", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.supplier_name


class Inventory(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255)
    product_image = models.ImageField(
        upload_to="product_images/", null=True, blank=True
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    quantity_in_stock = models.IntegerField()
    reorder_level = models.IntegerField()
    unit_price = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_name


class Sales(models.Model):
    sale_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    quantity_sold = models.IntegerField()
    sale_price = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ("completed", "Completed"),
            ("pending", "Pending"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
    )
    sale_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk is None:
            if self.product.quantity_in_stock < self.quantity_sold:
                raise ValueError("Not enough stock available for this sale.")
            self.product.quantity_in_stock -= self.quantity_sold
            self.product.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sale {self.sale_id} - {self.product.product_name}"
