document.addEventListener('DOMContentLoaded', () => {
    // Create notification center
    const notificationCenter = document.createElement('div');
    notificationCenter.className = 'notification-center';
    document.body.appendChild(notificationCenter);

    // DOM Elements
    const foodGrid = document.querySelector('.food-grid');
    const addForm = document.getElementById('addItemForm');
    const sidebarAddBtn = document.getElementById('sidebarAddBtn');
    const sortButton = document.querySelector('.filter-button');
    const searchInput = document.querySelector('.search-bar input');
    const uploadBtn = document.getElementById('uploadBtn');
    const photoUpload = document.getElementById('photoUpload');
    const resultsGrid = document.querySelector('.results-grid');

    // State
    let notifiedItems = new Set();
    let isSorted = false;

    // Initialization
    fetchFoodItems();
    setupNotificationCheck();
    fetchAnalysisResults();

    // Event Listeners
    sidebarAddBtn.addEventListener('click', () => {
        addForm.classList.toggle('hidden');
        if (!addForm.classList.contains('hidden')) {
            addForm.reset();
            document.getElementById('name').focus();
        }
    });

    addForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const newItem = {
            name: document.getElementById('name').value,
            category: document.getElementById('category').value.toLowerCase(),
            expiryDate: document.getElementById('expiryDate').value,
            quantity: parseInt(document.getElementById('quantity').value),
            unit: document.getElementById('unit').value
        };

        try {
            const response = await fetch('/api/items', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(newItem)
            });

            if (response.ok) {
                addForm.reset();
                addForm.classList.add('hidden');
                fetchFoodItems(isSorted, searchInput.value);
                showNotification('Item Added!', `${newItem.name} was successfully added.`, 'success');
            } else {
                const errorData = await response.json();
                showNotification('Error', errorData.error || 'Failed to add item.', 'error');
            }
        } catch (error) {
            showNotification('Network Error', 'Could not connect to the server to add item.', 'error');
        }
    });

    sortButton.addEventListener('click', () => {
        isSorted = !isSorted;
        sortButton.classList.toggle('active');
        fetchFoodItems(isSorted, searchInput.value);
    });

    searchInput.addEventListener('input', () => {
        fetchFoodItems(isSorted, searchInput.value);
    });

    uploadBtn.addEventListener('click', handlePhotoUpload);

    // Core Functions
    async function fetchFoodItems(sorted = false, searchTerm = '') {
        try {
            let url = '/api/items';
            const params = new URLSearchParams();
            if (sorted) params.append('sorted', 'true');
            if (searchTerm) params.append('search', searchTerm);
            if (params.toString()) url += `?${params.toString()}`;
            
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch food items.');
            const foodItems = await response.json();
            renderFoodItems(foodItems);
        } catch (error) {
            showNotification('Error', `Failed to load food items: ${error.message}`, 'error');
        }
    }

    async function handlePhotoUpload() {
        if (!photoUpload.files || photoUpload.files.length === 0) {
            showNotification('Error', 'Please select a photo first.', 'error');
            return;
        }

        const file = photoUpload.files[0];
        const formData = new FormData();
        formData.append('photo', file);

        try {
            showNotification('Processing', 'Analyzing your photo...', 'warning');
            const response = await fetch('/photo_handler', {method: 'POST', body: formData});
            const result = await response.json();
            
            if (result.status === 'success' || result.status === 'partial_success') {
                showNotification('Success', 'Photo analysis completed!', 'success');
                fetchAnalysisResults();
            } else {
                showNotification('Error', result.message || 'Failed to analyze photo', 'error');
            }
        } catch (error) {
            showNotification('Error', 'Failed to upload and analyze photo', 'error');
        }
    }

    async function fetchAnalysisResults() {
        try {
            const response = await fetch('/api/analysis_results');
            if (!response.ok) throw new Error('Failed to fetch analysis results');
            const results = await response.json();
            renderAnalysisResults(results);
        } catch (error) {
            showNotification('Error', 'Failed to load analysis results', 'error');
        }
    }

    function renderAnalysisResults(results) {
        resultsGrid.innerHTML = '';
        if (results.length === 0) {
            resultsGrid.innerHTML = '<p>No analysis results yet. Upload a photo to get started!</p>';
            return;
        }

        results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        results.forEach(result => {
            const card = document.createElement('div');
            card.className = 'analysis-card';
            
            const timestamp = new Date(result.timestamp).toLocaleString();
            card.innerHTML = `<h3>Analysis: ${timestamp}</h3>`;
            
            if (result.items && Array.isArray(result.items)) {
                result.items.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'analysis-item';
                    const expiryClass = item.expiration <= 0 ? 'expiry' : 'expiry fresh';
                    itemDiv.innerHTML = `
                        <span class="product">${item.product}</span>
                        <span class="quantity">${item.quantity} units</span>
                        <span class="${expiryClass}">${item.expiration <= 0 ? 'Expired' : `${item.expiration} days`}</span>
                    `;
                    card.appendChild(itemDiv);
                });
            } else {
                card.innerHTML += '<p>No items detected in this analysis.</p>';
            }
            
            const addToInventoryBtn = document.createElement('button');
            addToInventoryBtn.className = 'submit-item-button';
            addToInventoryBtn.textContent = 'Add to Inventory';
            addToInventoryBtn.addEventListener('click', () => {
                addAnalysisToInventory(result.items);
            });
            card.appendChild(addToInventoryBtn);
            
            resultsGrid.appendChild(card);
        });
    }

    async function addAnalysisToInventory(items) {
        if (!items || !Array.isArray(items)) {
            showNotification('Error', 'No valid items to add', 'error');
            return;
        }

        try {
            let addedCount = 0;
            for (const item of items) {
                const expiryDate = new Date();
                expiryDate.setDate(expiryDate.getDate() + item.expiration);
                const formattedDate = expiryDate.toISOString().split('T')[0];
                
                const newItem = {
                    name: item.product,
                    category: 'other',
                    expiryDate: formattedDate,
                    quantity: item.quantity,
                    unit: 'units'
                };

                const response = await fetch('/api/items', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(newItem)
                });

                if (response.ok) addedCount++;
            }
            
            showNotification('Success', `Added ${addedCount} items to inventory`, 'success');
            fetchFoodItems();
        } catch (error) {
            showNotification('Error', 'Failed to add some items to inventory', 'error');
        }
    }

    function setupNotificationCheck() {
        checkExpiringItems();
        setInterval(checkExpiringItems, 3600000); // Check every hour
    }

    async function checkExpiringItems() {
        try {
            const response = await fetch('https://armada-ribk.onrender.com/api/items'); 
            if (!response.ok) throw new Error('Failed to fetch items for notification check.');
            const foodItems = await response.json();

            const now = new Date();
            const oneDayInMs = 24 * 60 * 60 * 1000;

            foodItems.forEach(item => {
                const expiryDate = new Date(item.expiryDate); 
                const daysUntilExpiry = Math.ceil((expiryDate - now) / oneDayInMs);
                const itemKey = `${item._id}-${daysUntilExpiry}`;

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
                        `Quantity: ${item.quantity} ${item.unit}`,
                        "error"
                    );
                    notifiedItems.add(itemKey);
                }
            });
        } catch (error) {
            console.error('Error in checkExpiringItems:', error);
        }
    }

    function showNotification(title, message, type = 'warning') {
        const icons = {warning: '🚨', error: '❌', success: '✅'};
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <strong>${icons[type]} ${title}</strong>
            <span>${message}</span>
            <span class="notification-close">×</span>
        `;
        
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        notificationCenter.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease-out forwards';
            notification.addEventListener('animationend', () => notification.remove());
        }, 5000);
    }

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
            dairy: "dairy", produce: "produce", meat: "meat",
            grains: "grains", beverages: "beverages", condiments: "condiments"
        };
        const safeCategory = String(category).toLowerCase();
        return colors[safeCategory] || "other";
    }

    function formatExpiryText(date) {
        const status = getExpiryStatus(date);
        if (status === "expired") return "Expired";
        const d = new Date(date);
        return `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getFullYear().toString().slice(-2)}`;
    }

    function renderFoodItems(foodItems) {
        foodGrid.innerHTML = '';
        if (foodItems.length === 0) {
            foodGrid.innerHTML = '<p class="no-items-message">No food items found. Add some to get started!</p>';
            return;
        }
        
        foodItems.forEach(item => {
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

            // Button Container
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'button-container';

            // Remove One Button
            const deleteBtn = document.createElement('button');
            deleteBtn.classList.add('delete-btn');
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i> Remove One';
            deleteBtn.addEventListener('click', async () => {
                const confirmAction = confirm(`Remove one unit of "${item.name}"? (Current quantity: ${item.quantity})`);
                if (!confirmAction) return;

                try {
                    const response = await fetch(`/api/items/${item._id}`, {
                        method: 'DELETE'
                    });
                    const result = await response.json();
                    if (response.ok) {
                        showNotification('Success', result.message, 'success');
                        fetchFoodItems(isSorted, searchInput.value);
                    } else {
                        showNotification('Error', result.error || 'Failed to remove item.', 'error');
                    }
                } catch (error) {
                    showNotification('Network Error', 'Could not connect to the server to remove item.', 'error');
                }
            });
            buttonContainer.appendChild(deleteBtn);

            // Add One Button
            const addBtn = document.createElement('button');
            addBtn.classList.add('add-btn');
            addBtn.innerHTML = '<i class="fas fa-plus"></i> Add One';
            addBtn.addEventListener('click', async () => {
                const confirmAction = confirm(`Add one unit of "${item.name}"? (Current quantity: ${item.quantity})`);
                if (!confirmAction) return;

                try {
                    const response = await fetch(`/api/items/${item._id}/increment`, {
                        method: 'POST'
                    });
                    const result = await response.json();
                    if (response.ok) {
                        showNotification('Success', result.message, 'success');
                        fetchFoodItems(isSorted, searchInput.value);
                    } else {
                        showNotification('Error', result.error || 'Failed to add item.', 'error');
                    }
                } catch (error) {
                    showNotification('Network Error', 'Could not connect to the server to add item.', 'error');
                }
            });
            buttonContainer.appendChild(addBtn);

            // Edit Expiry Button
            const editExpiryBtn = document.createElement('button');
            editExpiryBtn.classList.add('edit-expiry-btn');
            editExpiryBtn.innerHTML = '<i class="fas fa-calendar-alt"></i> Edit Expiry';
            editExpiryBtn.addEventListener('click', () => {
                const dateInput = document.createElement('input');
                dateInput.type = 'date';
                dateInput.value = item.expiryDate;
                dateInput.classList.add('expiry-input');
                
                const confirmBtn = document.createElement('button');
                confirmBtn.textContent = 'Confirm';
                confirmBtn.classList.add('confirm-btn');

                const cancelBtn = document.createElement('button');
                cancelBtn.textContent = 'Cancel';
                cancelBtn.classList.add('cancel-btn');

                const editContainer = document.createElement('div');
                editContainer.className = 'edit-expiry-container';
                editContainer.appendChild(dateInput);
                editContainer.appendChild(confirmBtn);
                editContainer.appendChild(cancelBtn);

                expiryDiv.replaceChildren(editContainer);

                confirmBtn.addEventListener('click', async () => {
                    if (!dateInput.value) {
                        showNotification('Error', 'Please select a valid date.', 'error');
                        return;
                    }
                    try {
                        const response = await fetch(`/api/items/${item._id}/update_expiry`, {
                            method: 'PATCH',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ expiryDate: dateInput.value })
                        });
                        const result = await response.json();
                        if (response.ok) {
                            showNotification('Success', result.message, 'success');
                            fetchFoodItems(isSorted, searchInput.value);
                        } else {
                            showNotification('Error', result.error || 'Failed to update expiry date.', 'error');
                            expiryDiv.textContent = `Expires: ${formatExpiryText(item.expiryDate)}`;
                        }
                    } catch (error) {
                        showNotification('Network Error', 'Could not connect to the server to update expiry.', 'error');
                        expiryDiv.textContent = `Expires: ${formatExpiryText(item.expiryDate)}`;
                    }
                });

                cancelBtn.addEventListener('click', () => {
                    expiryDiv.textContent = `Expires: ${formatExpiryText(item.expiryDate)}`;
                });
            });
            buttonContainer.appendChild(editExpiryBtn);

            foodCard.appendChild(buttonContainer);
            foodGrid.appendChild(foodCard);
        });
    }
});