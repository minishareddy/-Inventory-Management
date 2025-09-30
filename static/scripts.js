document.addEventListener("DOMContentLoaded", () => {
    setInterval(fetchNotifications, 1000);
    initializePasswordToggle();
});

const popupMap = {
    sales: "addSalePopup",
    profile: "updatePopup",
    Iadd: "addProductPopup",
    Iupdate: "updateProductPopup"
};

function initializePasswordToggle() {
    document.querySelectorAll(".toggle-password").forEach(icon => {
        icon.addEventListener("click", () => togglePassword(icon));
    });
}

function togglePassword(icon) {
    const targetId = icon.getAttribute("data-target");
    const passwordField = document.getElementById(targetId);
    if (!passwordField) return;
    passwordField.type = passwordField.type === "password" ? "text" : "password";
    icon.classList.toggle("fa-lock");
    icon.classList.toggle("fa-unlock");
}

async function fetchNotifications() {
    try {
        const response = await fetch('/api/notifications/');
        const data = await response.json();
        updateNotifications(data.unread_count);
    } catch (error) {
        console.error('Error fetching notifications:', error);
    }
}

function updateNotifications(unreadCount) {
    const notificationCount = document.getElementById('notificationCount');
    notificationCount.textContent = unreadCount;
    notificationCount.style.display = unreadCount > 0 ? 'inline-block' : 'none';
}

function openPopup(productId, type) {
    const popupId = popupMap[type];
    if (!popupId) return;
    const popupElement = document.getElementById(popupId);
    popupElement.style.display = "block";
    if (type === 'Iupdate' && productId) {
        fetchProductData(productId);
    }
}

async function fetchProductData(productId) {
    try {
        const response = await fetch(`api/get-product/${productId}/`);
        const data = await response.json();
        populateProductFields(data);
    } catch (error) {
        console.error("Error fetching product data:", error);
    }
}

function populateProductFields(data) {
    const fields = {
        updateProductId: data.product_id,
        updateProductName: data.product_name,
        updateProductCategory: data.category_id,
        updateProductSupplier: data.supplier_id,
        updateProductStock: data.quantity_in_stock,
        updateReorderLevel: data.reorder_level,
        updateProductPrice: data.unit_price
    };

    Object.entries(fields).forEach(([id, value]) => {
        const field = document.getElementById(id);
        if (field) field.value = value;
    });
}

function closePopup(type) {
    const popupId = popupMap[type];
    if (!popupId) return;
    const popupElement = document.getElementById(popupId);
    popupElement.style.display = "none";
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

async function updateProduct() {
    const formData = new FormData(document.getElementById("updateProductForm"));
    formData.append("csrfmiddlewaretoken", getCSRFToken());
    const productId = document.getElementById("updateProductId").value;
    try {
        const response = await fetch(`/api/update/${productId}/`, {
            method: "POST",
            body: formData
        });
        const data = await response.json();
        handleResponse(data, "Product updated successfully!", "Error updating product!");
    } catch (error) {
        console.error("Error updating product:", error);
    }
}

async function deleteProduct(productId) {
    try {
        const response = await fetch(`/api/delete/${productId}/`, {
            method: "DELETE",
            headers: { "X-CSRFToken": getCSRFToken() }
        });
        const data = await response.json();
        if (data.status === "deleted") {
            alert("Product deleted successfully!");
            document.getElementById(`product-${productId}`).remove();
        } else {
            alert("Error deleting product!");
        }
    } catch (error) {
        console.error("Error deleting product:", error);
    }
}

async function addProduct() {
    const formData = new FormData(document.getElementById("addProductForm"));
    formData.append("csrfmiddlewaretoken", getCSRFToken());

    try {
        const response = await fetch("/api/add/", {
            method: "POST",
            body: formData
        });
        const data = await response.json();
        handleResponse(data, "Product added successfully!", "Error adding product!");
    } catch (error) {
        console.error("Error adding product:", error);
    }
}

function handleResponse(data, successMessage, errorMessage) {
    if (data.status === "success") {
        alert(successMessage);
        location.reload();
    } else {
        alert(errorMessage);
    }
}

function addSale() {
    let saleData = {
        product: document.getElementById("saleProduct").value,
        quantity: document.getElementById("saleQuantity").value,
        total_price: document.getElementById("saleTotalPrice").value,
        status: document.getElementById("saleStatus").value,
    };
    fetch("/sales/add/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": "{{ csrf_token }}" },
        body: JSON.stringify(saleData),
    }).then(response => response.json()).then(data => {
        alert(data.message || data.error);
        location.reload();
    });
}