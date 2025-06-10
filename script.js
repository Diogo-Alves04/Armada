document.addEventListener('DOMContentLoaded', () => {
    // Create notification center container
    const notificationCenter = document.createElement('div');
    notificationCenter.className = 'notification-center';
    document.body.appendChild(notificationCenter);

    // Food items array with test items (modify dates for testing)
    let foodItems = [
        {
            id: "1",
            name: "Milk",
            category: "dairy",
            expiryDate: new Date(Date.now() + 86400000).toISOString().split('T')[0], // Tomorrow
            quantity: 1,
            unit: "gallon"
        },
        {
            id: "2",
            name: "Apples",
            category: "produce",
            expiryDate: new Date(Date.now() - 86400000).toISOString().split('T')[0], // Yesterday
            quantity: 6,
            unit: "pieces"
        },
        {
            id: "3",
            name: "Chicken Breast",
            category: "meat",
            expiryDate: "2025-06-20",
            quantity: 2,
            unit: "lbs"
        },
        {
            id: "4",
            name: "Bread",
            category: "grains",
            expiryDate: "2025-06-03",
            quantity: 1,
            unit: "loaf"
        }
    ];

    // DOM Elements
    const foodGrid = document.querySelector('.food-grid');
    const addForm = document.getElementById('addItemForm');
    const sidebarAddBtn = document.getElementById('sidebarAddBtn');
    const sortButton = document.querySelector('.filter-button');
    const searchInput = document.querySelector('.search-bar input');
    const notificationsBtn = document.getElementById('notificationsBtn');
    const notificationForm = document.getElementById('notificationForm');
    const yesButton = document.querySelector('.notification-option.yes');
    const noButton = document.querySelector('.notification-option.no');

    // Notification state
    let notificationEnabled = localStorage.getItem('notificationsEnabled') === 'true';
    let notifiedItems = new Set();

    // Initialize
    let isSorted = false;
    renderFoodItems();
    setupNotificationCheck();

    // Toggle form visibility
    sidebarAddBtn.addEventListener('click', () => {
        addForm.classList.toggle('hidden');
    });

    // Form submission
    addForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const newItem = {
            id: Date.now().toString(),
            name: document.getElementById('name').value,
            category: document.getElementById('category').value.toLowerCase(),
            expiryDate: document.getElementById('expiryDate').value,
            quantity: parseInt(document.getElementById('quantity').value),
            unit: document.getElementById('unit').value
        };

        foodItems.push(newItem);
        addForm.reset();
        addForm.classList.add('hidden');
        renderFoodItems();
        checkExpiringItems(); // Check after adding new item
    });

    // Sort by expiry functionality
    sortButton.addEventListener('click', () => {
        if (!isSorted) {
            foodItems.sort((a, b) => {
                const statusA = getExpiryStatus(a.expiryDate);
                const statusB = getExpiryStatus(b.expiryDate);
                const statusOrder = { expired: 0, soon: 1, fresh: 2 };
                
                if (statusOrder[statusA] !== statusOrder[statusB]) {
                    return statusOrder[statusA] - statusOrder[statusB];
                }
                return new Date(a.expiryDate) - new Date(b.expiryDate);
            });
            sortButton.classList.add('active');
        } else {
            foodItems.sort((a, b) => parseInt(a.id) - parseInt(b.id));
            sortButton.classList.remove('active');
        }
        isSorted = !isSorted;
        renderFoodItems();
    });

    // Search functionality
    searchInput.addEventListener('input', () => {
        renderFoodItems();
    });

    // Notification functions
    function setupNotificationCheck() {
        setInterval(checkExpiringItems, 5000); // Check every 5 seconds
        checkExpiringItems(); // Initial check
    }

    function checkExpiringItems() {
        const now = new Date();
        const oneDayInMs = 24 * 60 * 60 * 1000;
        
        foodItems.forEach(item => {
            const expiryDate = new Date(item.expiryDate);
            const daysUntilExpiry = Math.ceil((expiryDate - now) / oneDayInMs);
            const itemKey = `${item.id}-${daysUntilExpiry}`;
            
            if (daysUntilExpiry === 1 && !notifiedItems.has(itemKey)) {
                showNotification(
                    `${item.name} expires tomorrow!`,
                    `Quantity: ${item.quantity} ${item.unit}`,
                    "warning"
                );
                notifiedItems.add(itemKey);
            } else if (daysUntilExpiry <= 0 && !notifiedItems.has(itemKey)) {
                showNotification(
                    `${item.name} has expired!`,
                    "Please remove or consume it",
                    "error"
                );
                notifiedItems.add(itemKey);
            }
        });
    }

    function showNotification(title, message, type = 'warning') {
        const icons = {
            warning: '🚨',
            error: '❌',
            success: '✅'
        };
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <strong>${icons[type]} ${title}</strong>
            <span>${message}</span>
            <span class="notification-close">&times;</span>
        `;
        
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        notificationCenter.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease-out';
            notification.addEventListener('animationend', () => notification.remove());
        }, 5000);
    }

    // Helper functions
    function getExpiryStatus(date) {
        const now = new Date();
        const expiry = new Date(date);
        const diffDays = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        if (diffDays < 0) return "expired";
        if (diffDays <= 3) return "soon";
        return "fresh";
    }

    function getCategoryColorClass(category) {
        const colors = {
            dairy: "dairy",
            produce: "produce",
            meat: "meat",
            grains: "grains",
            beverages: "beverages",
            condiments: "condiments"
        };
        return colors[category] || "";
    }

    function formatExpiryText(date) {
        const status = getExpiryStatus(date);
        if (status === "expired") return "Expired";
        const options = { month: 'short', day: 'numeric' };
        return new Date(date).toLocaleDateString(undefined, options);
    }

    function renderFoodItems() {
        const searchTerm = searchInput.value.toLowerCase();
        foodGrid.innerHTML = '';
        
        const filteredItems = foodItems.filter(item => 
            item.name.toLowerCase().includes(searchTerm) || 
            item.category.toLowerCase().includes(searchTerm)
        );

        filteredItems.forEach(item => {
            const foodCard = document.createElement('div');
            foodCard.classList.add('food-item-card');

            const headerDiv = document.createElement('div');
            headerDiv.style.display = 'flex';
            headerDiv.style.justifyContent = 'space-between';
            headerDiv.style.alignItems = 'center';
            headerDiv.style.marginBottom = '10px';

            const nameHeading = document.createElement('h3');
            nameHeading.textContent = item.name;

            const categoryBadge = document.createElement('span');
            categoryBadge.classList.add('category-badge', getCategoryColorClass(item.category));
            categoryBadge.textContent = item.category.charAt(0).toUpperCase() + item.category.slice(1);

            headerDiv.appendChild(nameHeading);
            headerDiv.appendChild(categoryBadge);
            foodCard.appendChild(headerDiv);

            const quantityDiv = document.createElement('div');
            quantityDiv.classList.add('quantity');
            quantityDiv.textContent = `Quantity: ${item.quantity} ${item.unit}`;
            foodCard.appendChild(quantityDiv);

            const expiryDiv = document.createElement('div');
            expiryDiv.classList.add('expiry', getExpiryStatus(item.expiryDate));
            expiryDiv.textContent = `Expires: ${formatExpiryText(item.expiryDate)}`;
            foodCard.appendChild(expiryDiv);

            foodGrid.appendChild(foodCard);
        });
    }
});