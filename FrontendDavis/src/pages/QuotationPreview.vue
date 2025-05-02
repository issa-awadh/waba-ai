<template>
  <div class="cart-container">
    <h2>📄 Quotation Preview</h2>
    <div class="section-header main-header">
      <span class="section-count total-count">
        Total Sections: {{ productSections.length }}
      </span>
    </div>
    <div v-if="productSections.length">
      <div v-for="(section, sectionIdx) in productSections" :key="section.label" class="cart-section">
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
                <th>Description</th>
                <th>Unit Price</th>
                <th>Quantity</th>
                <th>Total</th>
                <th>Remove</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(p, i) in section.products" :key="p.model_number">
                <td>
                  <input v-model="p.product_name" readonly class="readonly" />
                </td>
                <td>
                  <input v-model="p.model_number" readonly class="readonly" />
                </td>
                <td>
                  <textarea v-model="p.description" readonly class="readonly description-area" rows="2"></textarea>
                </td>
                <td>
                  <span class="price-badge">{{ p.unit_price }}</span>
                </td>
                <td>
                  <input type="number" v-model.number="p.quantity" min="1" class="qty-input" />
                </td>
                <td>
                  <span class="price-badge">{{ (p.unit_price * p.quantity).toLocaleString() }}</span>
                </td>
                <td>
                  <button class="delete-btn" @click="removeProduct(sectionIdx, i)">
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
      <p class="empty-cart-msg">No products in quotation.</p>
    </div>

    <!-- Additional Costs Section -->
    <div class="additional-costs-section">
      <h3>Add Costs</h3>
      <div class="costs-add-bar">
        <select v-model="addCostType">
          <option disabled value="">Add cost...</option>
          <option v-for="option in availableCostOptions" :key="option.key" :value="option.key">{{ option.label }}</option>
        </select>
        <template v-if="addCostType !== 'other' && addCostType">
          <button class="add-btn" @click="handleAddCost" :disabled="!addCostType">Add</button>
        </template>
        <template v-else-if="addCostType === 'other'">
          <input v-model="newOtherLabel" placeholder="Cost Label" />
          <input type="number" v-model.number="newOtherAmount" min="0" placeholder="Amount" />
          <button class="add-btn" @click="tryAddOtherCost">Add</button>
          <button class="cancel-btn" @click="cancelOtherForm">Cancel</button>
        </template>
      </div>

      <div class="costs-table-section" v-if="allCosts.length">
        <h4>All Costs</h4>
        <table class="cart-table cost-table">
          <thead>
            <tr><th>Label</th><th>Amount</th><th>Remove</th></tr>
          </thead>
          <tbody>
            <tr v-for="(cost, i) in allCosts" :key="cost.key" :class="cost.preset ? '' : 'other-cost-row'">
              <td>
                <input v-if="cost.preset" v-model="cost.label" readonly class="readonly" />
                <span v-else style="color:#1749b1; font-weight:500;">{{ cost.label }}</span>
              </td>
              <td>
                <input v-if="cost.preset" type="number" v-model.number="cost.amount" min="0" />
                <span v-else style="color:#22314a; font-weight:600;">{{ cost.amount.toLocaleString() }}</span>
              </td>
              <td>
                <button class="delete-btn" @click="removeCustomCost(i)">
                  <span class="delete-icon">✕</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="total-row">
        <strong>Grand Total:</strong> {{ grandTotal.toLocaleString() }}
      </div>

      <button class="download-btn" @click="downloadExcel">Download Excel</button>

      <div class="preview-nav-btns">
        <router-link to="/quotation-cart" class="nav-btn">Go to Cart</router-link>
        <router-link to="/quotation-summary" class="nav-btn">Summary & Rationale</router-link>
        <router-link to="/proposal" class="nav-btn">Generate Proposal</router-link>
        <button class="nav-btn" @click="saveAndNavigate">Save & Preview Quotation</button>
      </div>
    </div>

    <!-- Rationale Section -->
    <div class="rationale-section">
      <h3>Rationale & Recommendations</h3>
      <div class="markdown-content" v-html="compiledRationale"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import MarkdownIt from 'markdown-it'
import { useRouter } from 'vue-router'

const router = useRouter()
const md = new MarkdownIt()

const productSections = ref([
  {
    label: 'Pretreatment',
    products: [
      { product_name: 'Multi-media filter', model_number: 'MMF-1500', description: 'Multi-media filter for sediment removal', unit_price: 500, quantity: 1 },
    ]
  },
  {
    label: 'RO',
    products: [
      { product_name: 'Reverse Osmosis Unit', model_number: 'RO-DSmart1500', description: 'Reverse Osmosis unit for desalination', unit_price: 1500, quantity: 1 },
    ]
  },
  {
    label: 'Post Treatment',
    products: [
      { product_name: 'UV Sterilizer', model_number: 'UV-400', description: 'UV sterilizer for disinfection', unit_price: 250, quantity: 1 },
    ]
  }
])

const PRESET_COST_OPTIONS = [
  { label: 'Transport', key: 'transport' },
  { label: 'Labor', key: 'labor' },
  { label: 'Installation', key: 'installation' },
]
const addedPresetCosts = ref([])
const customCosts = ref([])
const addCostType = ref("")
const newOtherLabel = ref("")
const newOtherAmount = ref(0)

const availableCostOptions = computed(() => {
  const preset = PRESET_COST_OPTIONS.filter(
    (opt) => !addedPresetCosts.value.some((c) => c.key === opt.key)
  )
  return [...preset, { label: 'Other', key: 'other' }]
})

function handleAddCost() {
  if (!addCostType.value) return
  if (addCostType.value === 'other') {
    return
  }
  const found = PRESET_COST_OPTIONS.find((c) => c.key === addCostType.value)
  if (found && !addedPresetCosts.value.some((c) => c.key === found.key)) {
    addedPresetCosts.value.push({ ...found, amount: 0, preset: true })
    addCostType.value = ""
  }
}

function tryAddOtherCost() {
  if (newOtherLabel.value && newOtherAmount.value > 0) {
    customCosts.value.push({
      label: newOtherLabel.value,
      amount: newOtherAmount.value,
      preset: false,
      key: Date.now() + Math.random(),
    })
    newOtherLabel.value = ""
    newOtherAmount.value = 0
    addCostType.value = ""
  }
}

function cancelOtherForm() {
  newOtherLabel.value = ""
  newOtherAmount.value = 0
  addCostType.value = ""
}

function removeCustomCost(idx) {
  if (idx < addedPresetCosts.value.length) {
    addedPresetCosts.value.splice(idx, 1)
  } else {
    customCosts.value.splice(idx - addedPresetCosts.value.length, 1)
  }
}

const allCosts = computed(() => [
  ...addedPresetCosts.value,
  ...customCosts.value
])

function removeProduct(sectionIdx, prodIdx) {
  productSections.value[sectionIdx].products.splice(prodIdx, 1)
}

const grandTotal = computed(() => {
  let total = 0
  productSections.value.forEach(section => {
    section.products.forEach(p => {
      total += (p.unit_price || 0) * (p.quantity || 0)
    })
  })
  allCosts.value.forEach(c => {
    total += c.amount || 0
  })
  return total
})

function downloadExcel() {
  const rows = []
  productSections.value.forEach(section => {
    section.products.forEach(p => {
      rows.push({
        Category: section.label,
        'Product Name': p.product_name,
        'Model Number': p.model_number,
        Description: p.description,
        'Unit Price': p.unit_price,
        Quantity: p.quantity,
        Total: p.unit_price * p.quantity
      })
    })
  })
  customCosts.value.forEach(c => {
    rows.push({
      Category: 'Custom Cost',
      'Product Name': c.label,
      'Model Number': '',
      Description: '',
      'Unit Price': '',
      Quantity: '',
      Total: c.amount
    })
  })
  rows.push({ Category: '', 'Product Name': '', 'Model Number': '', Description: '', 'Unit Price': '', Quantity: 'Grand Total', Total: grandTotal.value })
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Quotation')
  XLSX.writeFile(wb, 'quotation.xlsx')
}

const rationale = ref(`
## System Recommendations
- Implemented multi-stage filtration
- Included UV sterilization for safety
- Sized according to requirements

## Cost Benefits
1. Optimized component selection
2. Energy-efficient configuration
3. Long-term operational savings
`)

const compiledRationale = computed(() => {
  return md.render(rationale.value)
})

function saveAndNavigate() {
  // Prepare the data to be passed
  const quotationData = {
    products: productSections.value,
    costs: allCosts.value,
    total: grandTotal.value,
    rationale: rationale.value
  }
  
  // Store in localStorage (or your preferred state management)
  localStorage.setItem('quotationData', JSON.stringify(quotationData))
  
  // Navigate to preview
  router.push('/quotation-final')
}
</script>

<style scoped>
/* --- Cart Container and Section Styles --- */
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

.total-count {
  background: #f5f9fc;
  color: #2563eb;
  font-weight: 700;
  font-size: 1.1rem;
  margin-left: auto;
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

/* --- Additional Costs Section --- */
.additional-costs-section {
  margin-top: 2rem;
  background: #eaf2fd;
  border: 1.5px solid #4f8dfd;
  box-shadow: 0 2px 10px rgba(37,99,235,0.06);
  padding: 1.5rem 1.2rem 2rem 1.2rem;
  max-width: 700px;
  margin-left: auto;
  margin-right: auto;
  border-radius: 10px;
}

.costs-add-bar {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 1.2rem;
  background: #eaf2fd;
  border-radius: 8px;
  padding: 0.85rem 1rem;
  box-shadow: 0 1px 4px rgba(60,72,88,0.04);
}

.add-btn {
  background: #4f8dfd;
  color: #fff;
  border: none;
  padding: 7px 16px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 1rem;
  margin-left: 2px;
  cursor: pointer;
  transition: background 0.18s;
  display: flex;
  align-items: center;
}
.add-btn:hover {
  background: #2563eb;
}

.cancel-btn {
  background: #e0e6ed;
  color: #444;
  border: none;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 1rem;
  margin-left: 2px;
  cursor: pointer;
  transition: background 0.15s;
}
.cancel-btn:hover {
  background: #cfd8e3;
}

.download-btn {
  background: #4f8dfd;
  color: #fff;
  border: none;
  border-radius: 7px;
  padding: 8px 20px;
  font-size: 1.07rem;
  font-weight: 500;
  margin-top: 1.7rem;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(60,72,88,0.04);
  transition: background 0.16s;
}
.download-btn:hover {
  background: #2563eb;
}

.total-row {
  margin-top: 1.5rem;
  font-size: 1.15rem;
  color: #1749b1;
  font-weight: 600;
  text-align: right;
}

/* --- Navigation Buttons --- */
.preview-nav-btns {
  display: flex;
  gap: 1.2rem;
  margin-top: 2.2rem;
  margin-bottom: 0;
  justify-content: flex-end;
}
.nav-btn {
  background: #eaf2fd;
  color: #1749b1;
  border: 1.5px solid #1749b1;
  border-radius: 8px;
  padding: 0.65rem 1.5rem;
  font-size: 1.02rem;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.18s, color 0.18s;
  cursor: pointer;
  display: inline-block;
}
.nav-btn:hover {
  background: #1749b1;
  color: #fff;
}

/* --- Rationale Section --- */
.rationale-section {
  margin: 2.5rem 0 0 0;
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

.markdown-content {
  font-size: 1.05rem;
  color: #444;
  line-height: 1.7;
  white-space: pre-wrap;
}

.markdown-content :deep(h2) {
  color: #1749b1;
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  font-size: 1.4rem;
}

.markdown-content :deep(ul), 
.markdown-content :deep(ol) {
  padding-left: 1.5rem;
  margin: 1rem 0;
}

.markdown-content :deep(li) {
  margin: 0.5rem 0;
  color: #22314a;
}

.markdown-content :deep(p) {
  margin: 1rem 0;
  line-height: 1.7;
}

/* --- Inputs and Readonly --- */
.readonly {
  background-color: #f5f5f5;
  border: none;
  resize: none;
  width: 100%;
  font-size: 1rem;
  color: #222;
  padding: 6px 8px;
  border-radius: 6px;
}

.description-area {
  min-width: 220px;
  max-width: 420px;
  width: 100%;
  font-size: 1rem;
  padding: 6px 8px;
  border-radius: 6px;
  line-height: 1.4;
  background: #fafdff;
  color: #222;
  overflow-y: auto;
}

.qty-input {
  width: 60px;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1.5px solid #b5d6e6;
  background: #fff;
  color: #0066A1;
  font-size: 1rem;
  outline: none;
  transition: border 0.2s;
}
.qty-input:focus {
  border-color: #2C7DA0;
}
</style>
