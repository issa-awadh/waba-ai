<template>
  <div class="cart-container">
    <h2>🛒 Quotation Cart</h2>
    <div v-if="cartSections.length">
      <div v-for="(section, idx) in cartSections" :key="idx" class="cart-section">
        <div class="section-header">
          <h3>{{ section.label }}</h3>
          <span class="section-count">{{ section.products.length }} items</span>
        </div>
        <div class="table-wrapper">
          <table class="cart-table">
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Model</th>
                <th>Category</th>
                <th>Price</th>
                <th>Description</th>
                <th>Remove</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(product, pIdx) in section.products" :key="pIdx">
                <td>{{ product.product_name }}</td>
                <td>{{ product.model_number }}</td>
                <td>{{ product.category }}</td>
                <td>
                  <span class="price-badge">
                    {{ product.price ?? product.unit_price }}
                  </span>
                </td>
                <td>
                  <span class="desc-text">{{ product.product_description ?? product.description }}</span>
                </td>
                <td>
                  <button class="delete-btn" @click="removeProduct(section.label, product.model_number)">
                    <span class="delete-icon">🗑️</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <div v-else>
      <p class="empty-cart-msg">No products in cart.</p>
    </div>

    <div class="add-section">
      <h3>Add Product by Model Number</h3>
      <div class="add-controls">
        <input v-model="addModelNumber" placeholder="Enter model number" class="add-input"/>
        <select v-model="addSection" class="add-select">
          <option value="pretreatment">Pretreatment</option>
          <option value="ro">RO</option>
          <option value="posttreatment">Posttreatment</option>
        </select>
        <button class="add-btn" @click="addProduct">Add</button>
      </div>
    </div>

    <div class="rationale-section">
      <h3>Rationale</h3>
      <div class="rationale-content">{{ rationale }}</div>
    </div>

    <div class="preview-btn-row">
      <router-link to="/quotation-preview" class="preview-btn">
        <span class="preview-icon">📄</span>
        Quotation Preview
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const cartSections = ref<{ label: string, products: any[] }[]>([])
const rationale = ref('')
const addModelNumber = ref('')
const addSection = ref('pretreatment')

function getSectionKey(label: string) {
  if (label.toLowerCase().includes('pre')) return 'pretreatment'
  if (label.toLowerCase() === 'ro') return 'ro'
  if (label.toLowerCase().includes('post')) return 'posttreatment'
  return label.toLowerCase()
}

async function removeProduct(sectionLabel: string, model_number: string) {
  const sectionKey = getSectionKey(sectionLabel)
  await fetch('http://localhost:8000/api/recommendations/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section: sectionKey, model_number })
  })
  await loadCart()
}

async function addProduct() {
  if (!addModelNumber.value) return
  await fetch('http://localhost:8000/api/recommendations/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section: addSection.value, model_number: addModelNumber.value })
  })
  addModelNumber.value = ''
  await loadCart()
}

async function loadCart() {
  const recommendations = JSON.parse(localStorage.getItem('recommendations') || '{}')
  const rationaleVal = localStorage.getItem('rationale') || ''
  const pretreatment = recommendations.pretreatment || []
  const ro = recommendations.ro || recommendations.RO || []
  const posttreatment = recommendations.posttreatment || recommendations.postreatment || []
  cartSections.value = [
    { label: 'Pretreatment', products: pretreatment },
    { label: 'RO', products: ro },
    { label: 'Posttreatment', products: posttreatment }
  ]
  rationale.value = rationaleVal
}

onMounted(loadCart)
</script>

<style scoped>
.cart-container {
  max-width: 950px;
  margin: 2.5rem auto;
  background: #fff;
  padding: 2.5rem 2rem 2rem 2rem;
  border-radius: 16px;
  box-shadow: 0 6px 24px rgba(0, 102, 161, 0.10), 0 1.5px 4px rgba(44, 125, 160, 0.08);
  font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
}

h2 {
  color: #0066A1;
  margin-bottom: 1.5rem;
  font-size: 2.1rem;
  font-weight: 700;
  text-align: center;
  letter-spacing: 1px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.7rem;
}

.section-header h3 {
  color: #2C7DA0;
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.section-count {
  background: #eaf4fb;
  color: #0066A1;
  border-radius: 12px;
  padding: 0.2rem 0.8rem;
  font-size: 0.95rem;
  font-weight: 500;
}

.table-wrapper {
  overflow-x: auto;
  background: #f5f9fc;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(44, 125, 160, 0.07);
  margin-bottom: 2rem;
}

.cart-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: transparent;
}

.cart-table th {
  background: #eaf4fb;
  color: #0066A1;
  font-weight: 600;
  padding: 0.8rem 0.5rem;
  border-bottom: 2px solid #b5d6e6;
  text-align: left;
}

.cart-table td {
  background: #fff;
  padding: 0.7rem 0.5rem;
  border-bottom: 1px solid #eaeaea;
  vertical-align: top;
  transition: background 0.2s;
}

.cart-table tr:hover td {
  background: #f0f7fa;
}

.price-badge {
  background: #2C7DA0;
  color: #fff;
  padding: 0.25rem 0.7rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 1rem;
  letter-spacing: 0.5px;
  box-shadow: 0 1px 4px rgba(44, 125, 160, 0.10);
}

.desc-text {
  color: #555;
  font-size: 0.97rem;
}

.delete-btn {
  background: #fff;
  border: 1.5px solid #e57373;
  color: #e57373;
  border-radius: 6px;
  padding: 0.3rem 0.7rem;
  cursor: pointer;
  font-size: 1.1rem;
  transition: background 0.2s, color 0.2s, border 0.2s;
  box-shadow: 0 1px 4px rgba(229, 115, 115, 0.08);
}

.delete-btn:hover {
  background: #e57373;
  color: #fff;
  border-color: #e57373;
}

.delete-icon {
  font-size: 1.2rem;
}

.empty-cart-msg {
  color: #888;
  font-style: italic;
  text-align: center;
  margin: 2rem 0;
}

.add-section {
  margin-top: 2.5rem;
  background: #eaf4fb;
  border-radius: 10px;
  padding: 1.5rem 1rem;
  box-shadow: 0 1px 4px rgba(0,102,161,0.07);
}

.add-section h3 {
  color: #0066A1;
  margin-bottom: 1rem;
  font-size: 1.15rem;
  font-weight: 600;
}

.add-controls {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.add-input, .add-select {
  padding: 0.6rem 1rem;
  border: 1.5px solid #b5d6e6;
  border-radius: 7px;
  font-size: 1rem;
  background: #fff;
  color: #0066A1;
  outline: none;
  transition: border 0.2s;
}

.add-input:focus, .add-select:focus {
  border-color: #2C7DA0;
}

.add-btn {
  background: #0066A1;
  color: #fff;
  border: none;
  padding: 0.6rem 1.5rem;
  border-radius: 7px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
  box-shadow: 0 1px 4px rgba(0,102,161,0.10);
}

.add-btn:hover {
  background: #2C7DA0;
  box-shadow: 0 2px 8px rgba(0,102,161,0.13);
}

.rationale-section {
  margin-top: 2.5rem;
  background: #fffbe7;
  border-radius: 10px;
  padding: 1.5rem 1.2rem;
  box-shadow: 0 1px 4px rgba(255, 193, 7, 0.07);
}

.rationale-section h3 {
  color: #b48a00;
  margin-bottom: 1rem;
  font-size: 1.15rem;
  font-weight: 600;
}

.rationale-content {
  font-size: 1.05rem;
  color: #444;
  line-height: 1.7;
  white-space: pre-wrap;
}

.preview-btn-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 2.5rem;
}

.preview-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  background: linear-gradient(90deg, #2563eb 0%, #4f8dfd 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.85rem 2.1rem;
  font-size: 1.13rem;
  font-weight: 600;
  text-decoration: none;
  box-shadow: 0 2px 10px rgba(37,99,235,0.10);
  transition: background 0.18s, box-shadow 0.18s, transform 0.13s;
  cursor: pointer;
  margin-top: 1.5rem;
  letter-spacing: 0.5px;
}
.preview-btn:hover {
  background: linear-gradient(90deg, #1749b1 0%, #2563eb 100%);
  box-shadow: 0 4px 18px rgba(37,99,235,0.13);
  transform: translateY(-2px) scale(1.03);
  color: #fff;
}
.preview-icon {
  font-size: 1.35em;
  margin-right: 0.2em;
}
</style>
