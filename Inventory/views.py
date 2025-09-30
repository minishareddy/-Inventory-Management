from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from core.models import *
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import json
import joblib
import pandas as pd
import re
sales_model = joblib.load("ML/sales_prediction_model.joblib")
high_selling_model = joblib.load("ML/high_selling_classifier.joblib")


def remove_emojis(text):
    """Remove emojis from text."""
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # Emoticons
                               u"\U0001F300-\U0001F5FF"  # Symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # Transport & map symbols
                               u"\U0001F700-\U0001F77F"  # Alchemical symbols
                               u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
                               u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                               u"\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
                               u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                               u"\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Extended-A
                               u"\U00002702-\U000027B0"  # Dingbats
                               u"\U000024C2-\U0001F251"  # Enclosed characters
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

def create_notification(user, message):
    clean_message = remove_emojis(message)
    Notification.objects.create(user=user, message=clean_message)



@csrf_protect
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = User.objects.get(username=username)
        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            create_notification(user, f"Welcome back, {user.username}!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "login.html", {"page_title": "Login"})


@csrf_protect
def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        role = request.POST.get("role", "staff")
        image = request.FILES.get("image")

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect("signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect("signup")

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.role = role

        if image:
            user.image = image

        user.save()
        login(request, user)
        messages.success(request, "Account created successfully!")
        return redirect("dashboard")

    return render(request, "signup.html", {"page_title": "Sign Up"})


@login_required
def logout_view(request):
    user = request.user
    logout(request)
    create_notification(user, "You have been logged out.")
    messages.success(request, "You have been logged out.")
    return redirect("login")


@login_required
def dashboard(request):
    sales_data = Sales.objects.select_related("product").all()
    inventory_data = Inventory.objects.all()

    sales_list = []
    for sale in sales_data:
        sales_list.append(
            {
                "sale_id": sale.sale_id,
                "product_name": (
                    sale.product.product_name if sale.product else "Unknown Product"
                ),
                "quantity_sold": sale.quantity_sold,
                "sale_price": float(sale.sale_price),
                "status": sale.status,
                "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
            }
        )

    sales_df = pd.DataFrame(sales_list)

    if not sales_df.empty:
        if "sale_date" in sales_df.columns:
            sales_df["sale_date"] = pd.to_datetime(
                sales_df["sale_date"], errors="coerce"
            )
            sales_df["day"] = sales_df["sale_date"].dt.day
            sales_df["day_of_week"] = sales_df["sale_date"].dt.dayofweek
            sales_df["hour"] = sales_df["sale_date"].dt.hour
            sales_df["month"] = sales_df["sale_date"].dt.month
        else:
            sales_df["day"] = sales_df["day_of_week"] = sales_df["hour"] = sales_df[
                "month"
            ] = 0

        sales_df["status_encoded"] = (
            sales_df["status"].map({"completed": 1, "pending": 0}).fillna(0)
        )
        sales_df["sale_price"] = pd.to_numeric(
            sales_df["sale_price"], errors="coerce"
        ).fillna(0)

        features = [
            "quantity_sold",
            "sale_price",
            "status_encoded",
            "month",
            "day",
            "hour",
            "day_of_week",
        ]

        if all(col in sales_df.columns for col in features):
            sales_df["predicted_sales"] = sales_model.predict(sales_df[features]).round(
                2
            )
            sales_df["high_selling"] = high_selling_model.predict(sales_df[features])
        else:
            sales_df["predicted_sales"] = 0
            sales_df["high_selling"] = 0
    else:
        sales_df = pd.DataFrame(
            columns=["sale_price", "high_selling", "predicted_sales"]
        )

    sales_list = sales_df.to_dict(orient="records")

    for sale in sales_list:
        if isinstance(sale.get("sale_date"), pd.Timestamp):
            sale["sale_date"] = sale["sale_date"].isoformat()

    # 🚀 Send Notification with Predictions & Sales Info
    for sale in sales_list:
        message = f"""
        🔹 Product: {sale['product_name']}
        🔸 Sold: {sale['quantity_sold']}
        🔹 Sale Price: ${sale['sale_price']}
        🔸 Predicted Sales: {sale['predicted_sales']}
        🔹 High Selling Score: {sale['high_selling']}
        """
        create_notification(request.user, message.strip())

    context = {
        "total_sales": (
            sales_df["sale_price"].sum() if "sale_price" in sales_df.columns else 0
        ),
        "total_inventory": sum(item.quantity_in_stock for item in inventory_data),
        "new_orders": Sales.objects.filter(status="pending").count(),
        "revenue_growth": (
            f"{((sales_df['sale_price'].sum() / 1000000) * 100):.2f}%"
            if "sale_price" in sales_df.columns
            else "0%"
        ),
        "recent_sales": json.dumps(sales_list),
        "page_title": "Dashboard",
    }

    return render(request, "dashboard.html", context)


@login_required
def get_notifications(request):
    unread_count = Notification.objects.filter(
        user=request.user, status="unread"
    ).count()
    return JsonResponse({"unread_count": unread_count})


@login_required
def notifications_page(request):
    """Fetch all notifications for the logged-in user."""
    notifications = Notification.objects.filter(user=request.user).order_by(
        "-created_at"
    )
    return render(
        request,
        "notifications.html",
        {"notifications": notifications, "page_title": "Notifications"},
    )


@login_required
def mark_notification_as_read(request, notification_id):
    """Mark a notification as read."""
    notification = get_object_or_404(
        Notification, notification_id=notification_id, user=request.user
    )
    notification.status = "read"
    notification.save()
    return redirect("notifications")


@login_required
def inventory_page(request):
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    products = Inventory.objects.all()
    search_query = request.GET.get("search", "")
    if search_query:
        products = products.filter(product_name__icontains=search_query)

    category_filter = request.GET.get("category", "")
    if category_filter:
        products = products.filter(category_id=category_filter)

    stock_filter = request.GET.get("stock", "")
    if stock_filter == "low":
        products = products.filter(quantity_in_stock__lte=10)
    elif stock_filter == "high":
        products = products.filter(quantity_in_stock__gt=10)

    price_filter = request.GET.get("price", "")
    if price_filter == "low":
        products = products.filter(unit_price__lt=50)
    elif price_filter == "mid":
        products = products.filter(unit_price__gte=50, unit_price__lte=200)
    elif price_filter == "high":
        products = products.filter(unit_price__gt=200)

    total_products = products.count()
    total_valuation = sum(
        product.unit_price * product.quantity_in_stock for product in products
    )
    low_stock_count = products.filter(quantity_in_stock__lte=10).count()

    return render(
        request,
        "inventory.html",
        {
            "products": products,
            "categories": categories,
            "suppliers": suppliers,
            "total_products": total_products,
            "total_valuation": total_valuation,
            "low_stock_count": low_stock_count,
            "page_title": "Inventory",
        },
    )


@login_required
def add_product(request):
    if request.method == "POST":
        product_name = request.POST.get("product_name")
        category_id = request.POST.get("category")
        supplier_id = request.POST.get("supplier")
        quantity = int(request.POST.get("quantity"))
        reorder_level = int(request.POST.get("reorder_level"))
        price = float(request.POST.get("price"))
        image = request.FILES.get("image")
        category = get_object_or_404(Category, category_id=category_id)
        supplier = get_object_or_404(Supplier, supplier_id=supplier_id)
        product = Inventory.objects.create(
            product_name=product_name,
            category=category,
            supplier=supplier,
            quantity_in_stock=quantity,
            reorder_level=reorder_level,
            unit_price=price,
            product_image=image,
        )

        return JsonResponse({"status": "success", "product_id": product.product_id})

    return JsonResponse({"status": "error"}, status=400)


@login_required
def update_product(request, product_id):
    product = get_object_or_404(Inventory, product_id=product_id)
    if request.method == "POST":
        product.product_name = request.POST.get("product_name")
        product.category = get_object_or_404(
            Category, category_id=request.POST.get("category")
        )
        product.supplier = get_object_or_404(
            Supplier, supplier_id=request.POST.get("supplier")
        )
        product.quantity_in_stock = int(request.POST.get("quantity"))
        product.reorder_level = int(request.POST.get("reorder_level"))
        product.unit_price = float(request.POST.get("price"))
        if "image" in request.FILES:
            product.product_image = request.FILES["image"]

        product.save()
        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error"}, status=400)


@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Inventory, product_id=product_id)
    product.delete()
    return JsonResponse({"status": "deleted", "product_id": product_id})


@login_required
def get_product(request, product_id):
    product = get_object_or_404(Inventory, product_id=product_id)
    data = {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "category_id": product.category.category_id,
        "supplier_id": product.supplier.supplier_id,
        "quantity_in_stock": product.quantity_in_stock,
        "reorder_level": product.reorder_level,
        "unit_price": float(product.unit_price),
    }
    return JsonResponse(data)


@login_required
def profile_view(request):
    if request.method == "POST":
        user = request.user
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")
        user.role = request.POST.get("role")
        if "image" in request.FILES:
            user.image = request.FILES["image"]

        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

    return render(request, "profile.html", {"page_title": "Profile"})


@login_required
def sales(request):
    sales = Sales.objects.all()
    products = Inventory.objects.all()
    total_revenue = sum(sale.quantity_sold * sale.sale_price for sale in sales)
    total_sales = sales.count()
    pending_payments = sum(
        sale.quantity_sold * sale.sale_price
        for sale in sales
        if sale.status == "pending"
    )
    average_order_value = total_revenue / total_sales if total_sales > 0 else 0
    best_selling_product = (
        Sales.objects.values("product__product_name")
        .annotate(total_quantity=models.Sum("quantity_sold"))
        .order_by("-total_quantity")
        .first()
    )
    context = {
        "sales": sales,
        "products": products,
        "total_revenue": total_revenue,
        "total_sales": total_sales,
        "pending_payments": pending_payments,
        "average_order_value": average_order_value,
        "best_selling_product": (
            best_selling_product["product__product_name"]
            if best_selling_product
            else "N/A"
        ),
        "page_title": "Sales",
    }

    return render(request, "sales.html", context)


@login_required
@csrf_exempt
def add_sale(request):
    if request.method == "POST":
        data = json.loads(request.body)
        product_id = data.get("product")
        quantity = int(data.get("quantity"))
        total_price = float(data.get("total_price"))
        status = data.get("status")
        try:
            product = Inventory.objects.get(product_id=product_id)
            if product.quantity_in_stock < quantity:
                return JsonResponse({"error": "Not enough stock available"}, status=400)
            else:
                Sales.objects.create(
                    product=product,
                    quantity_sold=quantity,
                    sale_price=total_price / quantity,
                    status=status,
                )
                product.quantity_in_stock -= quantity
                product.save()
                return JsonResponse({"message": "Sale added successfully!"})
        except Inventory.DoesNotExist:
            return JsonResponse({"error": "Product not found"}, status=400)
        except User.DoesNotExist:
            return JsonResponse({"error": "Customer not found"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def suppliers_list(request):
    suppliers = Supplier.objects.all()
    return render(
        request, "suppliers.html", {"suppliers": suppliers, "page_title": "Suppliers"}
    )


@login_required
def add_supplier(request):
    if request.method == "POST":
        supplier_name = request.POST.get("supplier_name")
        contact_person = request.POST.get("contact_person")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        address = request.POST.get("address")
        supplier_logo = request.FILES.get("supplier_logo")

        Supplier.objects.create(
            supplier_name=supplier_name,
            contact_person=contact_person,
            phone=phone,
            email=email,
            address=address,
            supplier_logo=supplier_logo,
        )
    return redirect("suppliers_list")


@login_required
def update_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)

    if request.method == "POST":
        supplier.supplier_name = request.POST.get("supplier_name")
        supplier.contact_person = request.POST.get("contact_person")
        supplier.phone = request.POST.get("phone")
        supplier.email = request.POST.get("email")
        supplier.address = request.POST.get("address")

        if "supplier_logo" in request.FILES:
            supplier.supplier_logo = request.FILES["supplier_logo"]

        supplier.save()
    return redirect("suppliers_list")


@login_required
def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    supplier.delete()
    return redirect("suppliers_list")
