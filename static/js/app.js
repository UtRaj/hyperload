let currentPage = 1;
let currentFilters = {};

function showToast(title, message, isError = false) {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');
    
    toastTitle.textContent = title;
    toastBody.textContent = message;
    
    toast.className = 'toast';
    if (isError) {
        toast.classList.add('bg-danger', 'text-white');
    } else {
        toast.classList.add('bg-success', 'text-white');
    }
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadProgress = document.getElementById('uploadProgress');
const progressBar = document.getElementById('progressBar');
const progressPercent = document.getElementById('progressPercent');
const progressStatus = document.getElementById('progressStatus');
const progressMessage = document.getElementById('progressMessage');

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

async function handleFileUpload(file) {
    if (!file.name.endsWith('.csv')) {
        showToast('Error', 'Please upload a CSV file', true);
        return;
    }
    
    uploadProgress.style.display = 'block';
    dropZone.style.display = 'none';
    progressBar.style.width = '0%';
    progressPercent.textContent = '0%';
    progressStatus.textContent = 'Uploading file...';
    progressMessage.textContent = '';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const data = await response.json();
        monitorProgress(data.task_id);
    } catch (error) {
        showToast('Upload Error', error.message, true);
        resetUploadUI();
    }
}

function monitorProgress(taskId) {
    const eventSource = new EventSource(`/api/progress/${taskId}`);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        const progress = Math.round(data.progress);
        progressBar.style.width = `${progress}%`;
        progressPercent.textContent = `${progress}%`;
        progressStatus.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        
        if (data.total_rows && data.processed_rows !== undefined) {
            progressMessage.textContent = `${data.processed_rows.toLocaleString()} / ${data.total_rows.toLocaleString()} products processed`;
        } else {
            progressMessage.textContent = data.message;
        }
        
        if (data.status === 'completed') {
            progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
            progressBar.classList.add('bg-success');
            showToast('Success', data.message);
            eventSource.close();
            
            setTimeout(() => {
                resetUploadUI();
                loadProducts();
            }, 2000);
        } else if (data.status === 'failed') {
            progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
            progressBar.classList.add('bg-danger');
            showToast('Import Failed', data.message, true);
            eventSource.close();
            
            setTimeout(resetUploadUI, 3000);
        }
    };
    
    eventSource.onerror = () => {
        eventSource.close();
        showToast('Error', 'Connection to server lost', true);
        resetUploadUI();
    };
}

function resetUploadUI() {
    uploadProgress.style.display = 'none';
    dropZone.style.display = 'block';
    fileInput.value = '';
}

async function loadProducts(page = 1) {
    currentPage = page;
    const searchTerm = document.getElementById('searchInput').value;
    const activeFilter = document.getElementById('activeFilter').value;
    
    const params = new URLSearchParams({
        page: page,
        per_page: 20
    });
    
    if (searchTerm) params.append('search', searchTerm);
    if (activeFilter) params.append('active', activeFilter);
    
    try {
        const response = await fetch(`/api/products?${params}`);
        const data = await response.json();
        
        renderProducts(data.items);
        renderPagination(data.page, data.pages, data.total);
    } catch (error) {
        showToast('Error', 'Failed to load products', true);
    }
}

function renderProducts(products) {
    const tbody = document.getElementById('productsTableBody');
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No products found</td></tr>';
        return;
    }
    
    tbody.innerHTML = products.map(product => `
        <tr>
            <td><strong>${escapeHtml(product.sku)}</strong></td>
            <td>${escapeHtml(product.name)}</td>
            <td class="text-truncate-custom">${escapeHtml(product.description || '-')}</td>
            <td>
                <span class="badge ${product.active ? 'bg-success' : 'bg-secondary'}">
                    ${product.active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary action-btn" onclick="editProduct(${product.id})">Edit</button>
                <button class="btn btn-sm btn-outline-danger action-btn" onclick="deleteProduct(${product.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function renderPagination(currentPage, totalPages, totalItems) {
    const paginationList = document.getElementById('paginationList');
    
    if (totalPages <= 1) {
        paginationList.innerHTML = `<li class="page-item disabled"><span class="page-link">Total: ${totalItems} products</span></li>`;
        return;
    }
    
    let html = '';
    
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadProducts(${currentPage - 1}); return false;">Previous</a>
        </li>
    `;
    
    const maxPages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(totalPages, startPage + maxPages - 1);
    
    if (endPage - startPage < maxPages - 1) {
        startPage = Math.max(1, endPage - maxPages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="loadProducts(${i}); return false;">${i}</a>
            </li>
        `;
    }
    
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadProducts(${currentPage + 1}); return false;">Next</a>
        </li>
    `;
    
    paginationList.innerHTML = html;
}

document.getElementById('searchBtn').addEventListener('click', () => loadProducts(1));
document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loadProducts(1);
});
document.getElementById('activeFilter').addEventListener('change', () => loadProducts(1));

document.getElementById('addProductBtn').addEventListener('click', () => {
    document.getElementById('productModalTitle').textContent = 'Add Product';
    document.getElementById('productForm').reset();
    document.getElementById('productId').value = '';
    document.getElementById('productActive').checked = true;
    
    const modal = new bootstrap.Modal(document.getElementById('productModal'));
    modal.show();
});

async function editProduct(id) {
    try {
        const response = await fetch(`/api/products/${id}`);
        const product = await response.json();
        
        document.getElementById('productModalTitle').textContent = 'Edit Product';
        document.getElementById('productId').value = product.id;
        document.getElementById('productSku').value = product.sku;
        document.getElementById('productName').value = product.name;
        document.getElementById('productDescription').value = product.description || '';
        document.getElementById('productActive').checked = product.active;
        
        const modal = new bootstrap.Modal(document.getElementById('productModal'));
        modal.show();
    } catch (error) {
        showToast('Error', 'Failed to load product', true);
    }
}

document.getElementById('saveProductBtn').addEventListener('click', async () => {
    const id = document.getElementById('productId').value;
    const data = {
        sku: document.getElementById('productSku').value,
        name: document.getElementById('productName').value,
        description: document.getElementById('productDescription').value || null,
        active: document.getElementById('productActive').checked
    };
    
    if (!data.sku || !data.name) {
        showToast('Validation Error', 'SKU and Name are required', true);
        return;
    }
    
    try {
        const url = id ? `/api/products/${id}` : '/api/products';
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Save failed');
        }
        
        showToast('Success', `Product ${id ? 'updated' : 'created'} successfully`);
        bootstrap.Modal.getInstance(document.getElementById('productModal')).hide();
        loadProducts(currentPage);
    } catch (error) {
        showToast('Error', error.message, true);
    }
});

async function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) return;
    
    try {
        const response = await fetch(`/api/products/${id}`, { method: 'DELETE' });
        
        if (!response.ok) {
            throw new Error('Delete failed');
        }
        
        showToast('Success', 'Product deleted successfully');
        loadProducts(currentPage);
    } catch (error) {
        showToast('Error', 'Failed to delete product', true);
    }
}

document.getElementById('bulkDeleteBtn').addEventListener('click', async () => {
    const confirmed = confirm('⚠️ WARNING: This will delete ALL products in the database. This action cannot be undone. Are you absolutely sure?');
    
    if (!confirmed) return;
    
    const doubleConfirm = confirm('Please confirm again: Delete ALL products?');
    
    if (!doubleConfirm) return;
    
    try {
        const response = await fetch('/api/products', { method: 'DELETE' });
        const data = await response.json();
        
        showToast('Success', data.message);
        loadProducts(1);
    } catch (error) {
        showToast('Error', 'Failed to delete products', true);
    }
});

async function loadWebhooks() {
    try {
        const response = await fetch('/api/webhooks');
        const webhooks = await response.json();
        renderWebhooks(webhooks);
    } catch (error) {
        showToast('Error', 'Failed to load webhooks', true);
    }
}

function renderWebhooks(webhooks) {
    const tbody = document.getElementById('webhooksTableBody');
    
    if (webhooks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No webhooks configured</td></tr>';
        return;
    }
    
    tbody.innerHTML = webhooks.map(webhook => `
        <tr>
            <td class="text-truncate-custom" title="${escapeHtml(webhook.url)}">${escapeHtml(webhook.url)}</td>
            <td>${escapeHtml(webhook.event_type)}</td>
            <td>
                <span class="badge ${webhook.enabled ? 'bg-success' : 'bg-secondary'}">
                    ${webhook.enabled ? 'Enabled' : 'Disabled'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-info action-btn" onclick="testWebhook(${webhook.id})">Test</button>
                <button class="btn btn-sm btn-outline-primary action-btn" onclick="editWebhook(${webhook.id})">Edit</button>
                <button class="btn btn-sm btn-outline-danger action-btn" onclick="deleteWebhook(${webhook.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

document.getElementById('addWebhookBtn').addEventListener('click', () => {
    document.getElementById('webhookModalTitle').textContent = 'Add Webhook';
    document.getElementById('webhookForm').reset();
    document.getElementById('webhookId').value = '';
    document.getElementById('webhookEnabled').checked = true;
    
    const modal = new bootstrap.Modal(document.getElementById('webhookModal'));
    modal.show();
});

async function editWebhook(id) {
    try {
        const response = await fetch('/api/webhooks');
        const webhooks = await response.json();
        const webhook = webhooks.find(w => w.id === id);
        
        if (!webhook) throw new Error('Webhook not found');
        
        document.getElementById('webhookModalTitle').textContent = 'Edit Webhook';
        document.getElementById('webhookId').value = webhook.id;
        document.getElementById('webhookUrl').value = webhook.url;
        document.getElementById('webhookEventType').value = webhook.event_type;
        document.getElementById('webhookEnabled').checked = webhook.enabled;
        
        const modal = new bootstrap.Modal(document.getElementById('webhookModal'));
        modal.show();
    } catch (error) {
        showToast('Error', 'Failed to load webhook', true);
    }
}

document.getElementById('saveWebhookBtn').addEventListener('click', async () => {
    const id = document.getElementById('webhookId').value;
    const data = {
        url: document.getElementById('webhookUrl').value,
        event_type: document.getElementById('webhookEventType').value,
        enabled: document.getElementById('webhookEnabled').checked
    };
    
    if (!data.url) {
        showToast('Validation Error', 'URL is required', true);
        return;
    }
    
    try {
        const url = id ? `/api/webhooks/${id}` : '/api/webhooks';
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Save failed');
        }
        
        showToast('Success', `Webhook ${id ? 'updated' : 'created'} successfully`);
        bootstrap.Modal.getInstance(document.getElementById('webhookModal')).hide();
        loadWebhooks();
    } catch (error) {
        showToast('Error', error.message, true);
    }
});

async function deleteWebhook(id) {
    if (!confirm('Are you sure you want to delete this webhook?')) return;
    
    try {
        const response = await fetch(`/api/webhooks/${id}`, { method: 'DELETE' });
        
        if (!response.ok) {
            throw new Error('Delete failed');
        }
        
        showToast('Success', 'Webhook deleted successfully');
        loadWebhooks();
    } catch (error) {
        showToast('Error', 'Failed to delete webhook', true);
    }
}

async function testWebhook(id) {
    try {
        showToast('Testing', 'Sending test webhook...');
        
        const response = await fetch(`/api/webhooks/${id}/test`, { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            showToast('Webhook Test Success', `${result.message} (Response time: ${result.response_time_ms}ms)`);
        } else {
            showToast('Webhook Test Failed', result.message, true);
        }
    } catch (error) {
        showToast('Error', 'Failed to test webhook', true);
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.getElementById('products-tab').addEventListener('click', () => {
    loadProducts(1);
});

document.getElementById('webhooks-tab').addEventListener('click', () => {
    loadWebhooks();
});

loadProducts(1);
