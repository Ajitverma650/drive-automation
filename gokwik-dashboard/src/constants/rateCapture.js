export const merchantSizeOptions = ['Long Tail', 'Mid Market', 'Enterprise', 'SMB']
export const merchantTypeOptions = ['D2C', 'Marketplace', 'B2B', 'Aggregator']
export const agencyOptions = ['Agency A', 'Agency B', 'Agency C']
export const productOptions = ['Checkout', 'KwikPass', 'KwikAds', 'RTO']
export const paymentTabs = ['EMI', 'UPI', 'NetBanking', 'Wallet', 'Credit Card', 'Debit Card', 'BNPL', 'COD', 'Others', 'PPCOD']
export const pricingTypes = ['Flat', 'Percentage', 'Tiered']
export const commissionTypes = ['Percentage', 'Flat', 'Tiered']

// Per-tab method options — EXACT match to real GoKwik dashboard dropdowns
export const tabMethodOptions = {
  'EMI': ['Cardless', 'Credit Card', 'Debit Card', 'Default'],
  'UPI': ['Credit Card', 'Debit Card', 'Default'],
  'NetBanking': ['Airtel', 'AXIS', 'Default', 'HDFC', 'ICICI', 'KOTAK', 'SBI'],
  'Wallet': ['Default', 'FreeCharge', 'HDFC', 'Payzapp'],
  'Credit Card': ['Amex', 'Corporate', 'Default', 'Diners', 'International', 'Maestro', 'Master', 'Visa'],
  'Debit Card': ['Below 2K', 'Above 2K', 'Default', 'Rupay'],
  'BNPL': ['Default', 'Lazypay', 'Pay Later', 'Simple', 'Snapmint'],
  'COD': ['Default'],
  'Others': ['CreditPay', 'Default', 'TwidPay'],
  'PPCOD': ['Default'],
}

// Per-tab label for the methods field (matches original GoKwik dashboard)
export const tabMethodLabel = {
  'EMI': 'Methods',
  'UPI': 'Methods',
  'NetBanking': 'Bank',
  'Wallet': 'Provider',
  'Credit Card': 'Network',
  'Debit Card': 'Network',
  'BNPL': 'Provider',
  'COD': 'Methods',
  'Others': 'Select',
  'PPCOD': 'Methods',
}

// Fallback for any tab not explicitly mapped
export const defaultMethodOptions = ['Default']

export const dummyMerchants = [
  {
    id: 'sandbox',
    name: 'Sandbox.GoKwik',
    agreement: {
      merchantAgreementFile: null,
      merchantAgreementName: '',
      startDate: '',
      endDate: '',
      merchantSize: '',
      merchantType: '',
      agency: '',
      agencyCommission: '',
      purchasedProducts: [],
    },
    agreementSaved: false,
  },
  {
    id: 'jaipur-masala',
    name: 'Jaipur Masala Co.',
    agreement: {
      merchantAgreementFile: { name: 'jaipur_agreement.pdf' },
      merchantAgreementName: 'jaipur_agreement.pdf',
      startDate: '2026-03-01',
      endDate: '2028-03-01',
      merchantSize: 'Long Tail',
      merchantType: 'D2C',
      agency: '',
      agencyCommission: '5',
      purchasedProducts: ['Checkout'],
    },
    agreementSaved: true,
  },
  {
    id: 'urban-threads',
    name: 'Urban Threads Fashion',
    agreement: {
      merchantAgreementFile: { name: 'urban_threads_contract.pdf' },
      merchantAgreementName: 'urban_threads_contract.pdf',
      startDate: '2026-01-15',
      endDate: '2027-01-15',
      merchantSize: 'Mid Market',
      merchantType: 'D2C',
      agency: 'Agency A',
      agencyCommission: '8',
      purchasedProducts: ['Checkout', 'KwikPass'],
    },
    agreementSaved: true,
  },
  {
    id: 'fresh-basket',
    name: 'FreshBasket Groceries',
    agreement: {
      merchantAgreementFile: { name: 'freshbasket_deal.docx' },
      merchantAgreementName: 'freshbasket_deal.docx',
      startDate: '2025-06-01',
      endDate: '2026-06-01',
      merchantSize: 'Enterprise',
      merchantType: 'Marketplace',
      agency: 'Agency B',
      agencyCommission: '3',
      purchasedProducts: ['Checkout', 'KwikAds', 'RTO'],
    },
    agreementSaved: true,
  },
  {
    id: 'techzone',
    name: 'TechZone Electronics',
    agreement: {
      merchantAgreementFile: null,
      merchantAgreementName: '',
      startDate: '',
      endDate: '',
      merchantSize: 'SMB',
      merchantType: 'B2B',
      agency: '',
      agencyCommission: '',
      purchasedProducts: [],
    },
    agreementSaved: false,
  },
]

export const buildEmptyCheckout = () => ({
  pricingStartDate: '',
  pricingEndDate: '',
  minimumGuarantee: '0',
  frequency: 'Monthly',
  platformFee: '0',
  platformFeeFreq: 'Quarterly',
})

export const getMethodsForTab = (tab) => tabMethodOptions[tab] || defaultMethodOptions

export const buildInitialTabData = () => {
  const data = {}
  paymentTabs.forEach((tab) => {
    const methods = getMethodsForTab(tab)
    data[tab] = {
      pricingType: 'Flat',
      commRow: { method: methods[0], commissionType: 'Percentage', value: '' },
      commissions: [],
    }
  })
  return data
}
