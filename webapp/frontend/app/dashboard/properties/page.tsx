'use client'

import { useState, useEffect } from 'react'
import { Table, Input, Select, Card, Typography, Space, Tag, Button, message, Collapse, InputNumber, Row, Col, Modal, AutoComplete } from 'antd'
import { SearchOutlined, EnvironmentOutlined, CheckCircleOutlined, CloseCircleOutlined, FilterOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import type { ColumnsType } from 'antd/es/table'

const { Title } = Typography
const { Search } = Input

interface Property {
  id: string
  name: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  province: string | null
  postal_code: string | null
  address_canonical: string | null
  latitude: number | null
  longitude: number | null
  geocode_source: string | null
  created_at: string
  updated_at: string
  brands?: { name: string }[]
  latest_transaction?: {
    transaction_date: string | null
    price: number | null
    buyer_name: string | null
    seller_name: string | null
  } | null
}

export default function PropertiesPage() {
  const router = useRouter()
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [searchText, setSearchText] = useState('')
  const [cityFilter, setCityFilter] = useState<string | undefined>(undefined)
  const [brandFilter, setBrandFilter] = useState<string | undefined>(undefined)
  const [buyerFilter, setBuyerFilter] = useState<string | undefined>(undefined)
  const [sellerFilter, setSellerFilter] = useState<string | undefined>(undefined)
  const [minPrice, setMinPrice] = useState<number | undefined>(undefined)
  const [maxPrice, setMaxPrice] = useState<number | undefined>(undefined)
  const [geocodedFilter, setGeocodedFilter] = useState<string | undefined>(undefined)
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })

  // Price range options starting at 500k
  const priceOptions = [
    { label: '$0', value: 0 },
    { label: '$500,000', value: 500000 },
    { label: '$1,000,000', value: 1000000 },
    { label: '$1,500,000', value: 1500000 },
    { label: '$2,000,000', value: 2000000 },
    { label: '$2,500,000', value: 2500000 },
    { label: '$3,000,000', value: 3000000 },
    { label: '$3,500,000', value: 3500000 },
    { label: '$4,000,000', value: 4000000 },
    { label: '$4,500,000', value: 4500000 },
    { label: '$5,000,000', value: 5000000 },
    { label: '$5,500,000', value: 5500000 },
    { label: '$6,000,000', value: 6000000 },
    { label: '$6,500,000', value: 6500000 },
    { label: '$7,000,000', value: 7000000 },
    { label: '$7,500,000', value: 7500000 },
    { label: '$8,000,000', value: 8000000 },
    { label: '$8,500,000', value: 8500000 },
    { label: '$9,000,000', value: 9000000 },
    { label: '$9,500,000', value: 9500000 },
    { label: '$10,000,000', value: 10000000 },
    { label: '$20,000,000', value: 20000000 },
    { label: '$30,000,000', value: 30000000 },
    { label: '$40,000,000', value: 40000000 },
    { label: '$50,000,000', value: 50000000 },
    { label: '$60,000,000', value: 60000000 },
    { label: '$70,000,000', value: 70000000 },
    { label: '$80,000,000', value: 80000000 },
    { label: '$90,000,000', value: 90000000 },
    { label: '$100,000,000', value: 100000000 },
    { label: '$200,000,000', value: 200000000 },
    { label: '$300,000,000', value: 300000000 },
    { label: '$400,000,000', value: 400000000 },
    { label: '$500,000,000', value: 500000000 },
    { label: '$600,000,000', value: 600000000 },
    { label: '$700,000,000', value: 700000000 },
    { label: '$800,000,000', value: 800000000 },
    { label: '$900,000,000', value: 900000000 },
    { label: '$1,000,000,000', value: 1000000000 },
  ]

  // Fetch properties from Supabase
  const fetchProperties = async () => {
    setLoading(true)
    try {
      // Check authentication status
      const { data: { session } } = await supabase.auth.getSession()
      console.log('Current auth session:', session)
      console.log('User authenticated:', !!session)

      if (!session) {
        message.warning('You are not authenticated. Please log in.')
        console.error('No active session found')
      }

      // Build base query - if filtering by brand, we need to join differently
      let query;

      if (brandFilter) {
        // When filtering by brand, we need to get distinct properties that have this brand
        query = supabase
          .from('properties')
          .select(`
            *,
            property_brand_links!inner(
              brands!inner(name)
            ),
            transactions!property_id(
              transaction_date,
              price,
              buyer_name,
              seller_name
            )
          `, { count: 'exact' })
          .eq('property_brand_links.brands.name', brandFilter)
          .eq('province', 'ON')
          .order('updated_at', { ascending: false })
      } else {
        // Normal query without brand filter
        query = supabase
          .from('properties')
          .select(`
            *,
            property_brand_links(
              brands(name)
            ),
            transactions!property_id(
              transaction_date,
              price,
              buyer_name,
              seller_name
            )
          `, { count: 'exact' })
          .eq('province', 'ON')
          .order('updated_at', { ascending: false })
      }

      // Apply other filters
      if (cityFilter) {
        query = query.eq('city', cityFilter)
      }

      if (geocodedFilter === 'geocoded') {
        query = query.not('latitude', 'is', null)
      } else if (geocodedFilter === 'not_geocoded') {
        query = query.is('latitude', null)
      }

      if (searchText) {
        query = query.or(`address_line1.ilike.%${searchText}%,city.ilike.%${searchText}%,postal_code.ilike.%${searchText}%,name.ilike.%${searchText}%`)
      }

      // Pagination
      const from = (pagination.current - 1) * pagination.pageSize
      const to = from + pagination.pageSize - 1
      query = query.range(from, to)

      const { data, error, count } = await query

      console.log('Supabase query result:', { data, error, count })

      if (error) {
        message.error('Failed to load properties: ' + error.message)
        console.error('Error fetching properties:', error)
        console.error('Full error details:', JSON.stringify(error, null, 2))
        return
      }

      console.log(`Loaded ${data?.length || 0} properties out of ${count} total`)

      // Transform the data to flatten brands
      // We need to fetch ALL brands for each property, not just the filtered one
      const propertyIds = (data || []).map((p: any) => p.id)

      // Fetch all brand links for these properties
      const { data: allBrandLinks } = await supabase
        .from('property_brand_links')
        .select('property_id, brands(name)')
        .in('property_id', propertyIds)

      // Create a map of property_id to brands
      const brandsByProperty = new Map<string, { name: string }[]>()
      allBrandLinks?.forEach((link: any) => {
        if (!brandsByProperty.has(link.property_id)) {
          brandsByProperty.set(link.property_id, [])
        }
        if (link.brands) {
          brandsByProperty.get(link.property_id)!.push(link.brands)
        }
      })

      let transformedData = (data || []).map((property: any) => {
        // Get the latest transaction (transactions are sorted by date DESC in the query)
        const latestTransaction = property.transactions && property.transactions.length > 0
          ? property.transactions.reduce((latest: any, current: any) => {
              if (!latest) return current
              if (!current.transaction_date) return latest
              if (!latest.transaction_date) return current
              return new Date(current.transaction_date) > new Date(latest.transaction_date) ? current : latest
            }, null)
          : null

        return {
          ...property,
          brands: brandsByProperty.get(property.id) || [],
          latest_transaction: latestTransaction
        }
      })

      // Apply client-side filters for buyer, seller, and price range
      if (buyerFilter) {
        transformedData = transformedData.filter(p =>
          p.latest_transaction?.buyer_name?.toLowerCase().includes(buyerFilter.toLowerCase())
        )
      }

      if (sellerFilter) {
        transformedData = transformedData.filter(p =>
          p.latest_transaction?.seller_name?.toLowerCase().includes(sellerFilter.toLowerCase())
        )
      }

      if (minPrice !== undefined) {
        transformedData = transformedData.filter(p =>
          p.latest_transaction?.price && p.latest_transaction.price >= minPrice
        )
      }

      if (maxPrice !== undefined) {
        transformedData = transformedData.filter(p =>
          p.latest_transaction?.price && p.latest_transaction.price <= maxPrice
        )
      }

      setProperties(transformedData)
      setPagination(prev => ({ ...prev, total: count || 0 }))
    } catch (error) {
      message.error('An unexpected error occurred')
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  // Fetch unique cities for filter dropdown
  const [cities, setCities] = useState<string[]>([])
  const fetchCities = async () => {
    console.log('Fetching cities...')

    try {
      // Fetch multiple batches to ensure we get all unique cities
      const batchSize = 1000
      const batches = 15 // Fetch up to 15k properties
      let allData: any[] = []

      for (let i = 0; i < batches; i++) {
        const from = i * batchSize
        const to = from + batchSize - 1

        const { data, error } = await supabase
          .from('properties')
          .select('city')
          .eq('province', 'ON')
          .not('city', 'is', null)
          .range(from, to)

        if (error) {
          console.error(`Error fetching batch ${i}:`, error)
          break
        }

        if (!data || data.length === 0) {
          console.log(`Batch ${i} returned no data, stopping`)
          break
        }

        allData = allData.concat(data)
        console.log(`Fetched batch ${i}: ${data.length} rows, total so far: ${allData.length}`)

        // If we got less than batchSize, we've reached the end
        if (data.length < batchSize) {
          break
        }
      }

      const uniqueCities = Array.from(new Set(allData.map(p => p.city).filter(Boolean))) as string[]
      uniqueCities.sort()
      console.log(`Loaded ${uniqueCities.length} unique cities from ${allData.length} properties`)
      console.log('All cities:', uniqueCities)
      setCities(uniqueCities)
    } catch (err) {
      console.error('Error in fetchCities:', err)
    }
  }

  // Fetch unique brands for filter dropdown
  const [brands, setBrands] = useState<string[]>([])
  const fetchBrands = async () => {
    const { data, error } = await supabase
      .from('brands')
      .select('name')
      .order('name')

    if (data && !error) {
      setBrands(data.map(b => b.name))
    }
  }

  // Fetch unique buyers for filter dropdown
  const [buyers, setBuyers] = useState<string[]>([])
  const fetchBuyers = async () => {
    const { data, error } = await supabase
      .from('transactions')
      .select('buyer_name')
      .not('buyer_name', 'is', null)
      .order('buyer_name')
      .limit(10000)

    if (error) {
      console.error('Error fetching buyers:', error)
      return
    }

    if (data) {
      const uniqueBuyers = Array.from(new Set(data.map(t => t.buyer_name).filter(Boolean))) as string[]
      console.log(`Loaded ${uniqueBuyers.length} unique buyers`)
      setBuyers(uniqueBuyers)
    }
  }

  // Fetch unique sellers for filter dropdown
  const [sellers, setSellers] = useState<string[]>([])
  const fetchSellers = async () => {
    const { data, error } = await supabase
      .from('transactions')
      .select('seller_name')
      .not('seller_name', 'is', null)
      .order('seller_name')
      .limit(10000)

    if (error) {
      console.error('Error fetching sellers:', error)
      return
    }

    if (data) {
      const uniqueSellers = Array.from(new Set(data.map(t => t.seller_name).filter(Boolean))) as string[]
      console.log(`Loaded ${uniqueSellers.length} unique sellers:`, uniqueSellers)
      setSellers(uniqueSellers)
    }
  }

  useEffect(() => {
    const loadFilters = async () => {
      await fetchCities()
      await fetchBrands()
      await fetchBuyers()
      await fetchSellers()

      // Debug log after all fetches complete
      setTimeout(() => {
        console.log('=== FILTER DATA DEBUG ===')
        console.log('Cities array:', cities)
        console.log('Brands array:', brands)
        console.log('Buyers array:', buyers)
        console.log('Sellers array:', sellers)
      }, 1000)
    }
    loadFilters()
  }, [])

  useEffect(() => {
    fetchProperties()
  }, [pagination.current, pagination.pageSize, cityFilter, brandFilter, geocodedFilter, searchText, buyerFilter, sellerFilter, minPrice, maxPrice])

  const columns: ColumnsType<Property> = [
    {
      title: 'Address',
      key: 'address',
      sorter: (a, b) => {
        const addrA = (a.address_canonical || a.address_line1 || '').toLowerCase()
        const addrB = (b.address_canonical || b.address_line1 || '').toLowerCase()
        return addrA.localeCompare(addrB)
      },
      render: (_, record) => {
        const fullAddress = record.address_canonical || record.address_line1 || 'N/A'

        // Remove city, province, postal code, and country from the address
        let cleanAddress = fullAddress

        // Remove common patterns at the end: ", City, Province PostalCode", ", City Province", etc.
        if (record.city) {
          cleanAddress = cleanAddress.replace(new RegExp(`,?\\s*${record.city}.*$`, 'i'), '')
        }

        // Also try to remove province and country if present
        cleanAddress = cleanAddress
          .replace(/,?\s*ON\s*$/i, '')
          .replace(/,?\s*Ontario\s*$/i, '')
          .replace(/,?\s*Canada\s*$/i, '')
          .replace(/,?\s*CA\s*$/i, '')
          .replace(/,?\s*[A-Z]\d[A-Z]\s*\d[A-Z]\d\s*$/i, '') // Postal code pattern
          .trim()

        return (
          <div style={{ fontWeight: 500 }}>
            {cleanAddress || 'N/A'}
          </div>
        )
      },
      width: '25%',
    },
    {
      title: 'City',
      dataIndex: 'city',
      key: 'city',
      sorter: (a, b) => (a.city || '').localeCompare(b.city || ''),
      width: '12%',
    },
    {
      title: 'Sale Date',
      key: 'sale_date',
      sorter: (a, b) => {
        const dateA = a.latest_transaction?.transaction_date ? new Date(a.latest_transaction.transaction_date).getTime() : 0
        const dateB = b.latest_transaction?.transaction_date ? new Date(b.latest_transaction.transaction_date).getTime() : 0
        return dateA - dateB
      },
      render: (_, record) => {
        const date = record.latest_transaction?.transaction_date
        return date ? new Date(date).toLocaleDateString('en-CA') : '-'
      },
      width: '10%',
    },
    {
      title: 'Sale Price',
      key: 'sale_price',
      sorter: (a, b) => {
        const priceA = a.latest_transaction?.price || 0
        const priceB = b.latest_transaction?.price || 0
        return priceA - priceB
      },
      render: (_, record) => {
        const price = record.latest_transaction?.price
        return price ? `$${price.toLocaleString()}` : '-'
      },
      width: '12%',
    },
    {
      title: 'Brands',
      key: 'brands',
      sorter: (a, b) => {
        const brandA = a.brands?.[0]?.name || ''
        const brandB = b.brands?.[0]?.name || ''
        return brandA.localeCompare(brandB)
      },
      render: (_, record) => {
        if (!record.brands || record.brands.length === 0) {
          return <span style={{ fontSize: '12px', color: '#8c8c8c' }}>-</span>
        }
        return (
          <Space size={[0, 4]} wrap>
            {record.brands.slice(0, 2).map((brand, idx) => (
              <Tag key={idx} color="blue" style={{ fontSize: '11px' }}>
                {brand.name}
              </Tag>
            ))}
            {record.brands.length > 2 && (
              <Tag style={{ fontSize: '11px' }}>+{record.brands.length - 2}</Tag>
            )}
          </Space>
        )
      },
      width: '13%',
    },
    {
      title: 'Buyer',
      key: 'buyer',
      sorter: (a, b) => {
        const buyerA = a.latest_transaction?.buyer_name || ''
        const buyerB = b.latest_transaction?.buyer_name || ''
        return buyerA.localeCompare(buyerB)
      },
      render: (_, record) => record.latest_transaction?.buyer_name || '-',
      width: '12%',
    },
    {
      title: 'Seller',
      key: 'seller',
      sorter: (a, b) => {
        const sellerA = a.latest_transaction?.seller_name || ''
        const sellerB = b.latest_transaction?.seller_name || ''
        return sellerA.localeCompare(sellerB)
      },
      render: (_, record) => record.latest_transaction?.seller_name || '-',
      width: '13%',
    },
  ]

  const handleTableChange = (newPagination: any) => {
    setPagination({
      current: newPagination.current,
      pageSize: newPagination.pageSize,
      total: pagination.total,
    })
  }

  const handleSearch = (value: string) => {
    setSearchText(value)
    setPagination(prev => ({ ...prev, current: 1 })) // Reset to first page on search
  }

  const handleReset = () => {
    setSearchText('')
    setCityFilter(undefined)
    setBrandFilter(undefined)
    setBuyerFilter(undefined)
    setSellerFilter(undefined)
    setMinPrice(undefined)
    setMaxPrice(undefined)
    setGeocodedFilter(undefined)
    setPagination(prev => ({ ...prev, current: 1 }))
  }

  const hasActiveFilters = () => {
    return cityFilter || brandFilter || buyerFilter || sellerFilter || minPrice !== undefined || maxPrice !== undefined
  }

  const getPriceLabel = () => {
    if (minPrice === undefined && maxPrice === undefined) return 'Price'
    if (minPrice === undefined) return `Up to ${priceOptions.find(p => p.value === maxPrice)?.label}`
    if (maxPrice === undefined) return `${priceOptions.find(p => p.value === minPrice)?.label}+`
    return `${priceOptions.find(p => p.value === minPrice)?.label} - ${priceOptions.find(p => p.value === maxPrice)?.label}`
  }

  return (
    <div>
      <Title level={2}>
        <EnvironmentOutlined /> Properties
      </Title>

      {/* Search Bar */}
      <Card style={{ marginBottom: 16 }}>
        <Search
          placeholder="Search address, city, postal code..."
          allowClear
          enterButton={<SearchOutlined />}
          size="large"
          style={{ width: '100%' }}
          onSearch={handleSearch}
          onChange={(e) => !e.target.value && setSearchText('')}
          value={searchText}
        />
      </Card>

      {/* Filter Buttons - Always Visible */}
      <Card style={{ marginBottom: 16 }}>
        {/* Debug info */}
        <div style={{ marginBottom: 8, fontSize: 12, color: '#666' }}>
          Loaded: {cities.length} cities, {brands.length} brands, {buyers.length} buyers, {sellers.length} sellers
          <br />
          Cities: {cities.slice(0, 10).join(', ')} ... {cities.slice(-5).join(', ')}
        </div>
        <Space wrap size="middle">
          {/* City Filter */}
          <Select
            placeholder="City"
            style={{ minWidth: 150 }}
            size="large"
            allowClear
            value={cityFilter}
            onChange={setCityFilter}
            showSearch
            virtual={false}
            listHeight={500}
            dropdownStyle={{ maxHeight: 500, overflow: 'auto' }}
            options={cities.map(city => ({ label: city, value: city }))}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
            }
          />

          {/* Brand Filter */}
          <Select
            placeholder="Brand"
            style={{ minWidth: 150 }}
            size="large"
            allowClear
            value={brandFilter}
            onChange={setBrandFilter}
            showSearch
            virtual
            listHeight={400}
            options={brands.map(brand => ({ label: brand, value: brand }))}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
            }
          />

          {/* Buyer Filter */}
          <Select
            placeholder="Buyer"
            style={{ minWidth: 150 }}
            size="large"
            allowClear
            value={buyerFilter}
            onChange={setBuyerFilter}
            showSearch
            virtual
            listHeight={400}
            options={buyers.map(buyer => ({ label: buyer, value: buyer }))}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
            }
            notFoundContent={buyers.length === 0 ? "No buyers in database" : "No results"}
          />

          {/* Seller Filter */}
          <Select
            placeholder="Seller"
            style={{ minWidth: 150 }}
            size="large"
            allowClear
            value={sellerFilter}
            onChange={setSellerFilter}
            showSearch
            virtual
            listHeight={400}
            options={sellers.filter(s => s && s.trim()).map(seller => ({ label: seller, value: seller }))}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
            }
            notFoundContent={sellers.length === 0 ? "No sellers in database" : "No results"}
          />

          {/* Price Filter Dropdown */}
          <Select
            placeholder="Price"
            value={getPriceLabel()}
            size="large"
            style={{ minWidth: 180 }}
            popupMatchSelectWidth={450}
            popupRender={() => (
              <div style={{ padding: '16px' }}>
                <Typography.Text strong style={{ display: 'block', marginBottom: 12 }}>Price</Typography.Text>
                <Row gutter={16}>
                  <Col span={12}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>Minimum</Typography.Text>
                    <Select
                      placeholder="$0"
                      style={{ width: '100%', marginTop: 4 }}
                      value={minPrice}
                      onChange={setMinPrice}
                      popupMatchSelectWidth={200}
                      showSearch={false}
                    >
                      <Select.Option value={0}>$0</Select.Option>
                      {priceOptions.slice(1).map(opt => (
                        <Select.Option key={opt.value} value={opt.value}>
                          {opt.label}
                        </Select.Option>
                      ))}
                    </Select>
                  </Col>
                  <Col span={12}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>Maximum</Typography.Text>
                    <Select
                      placeholder="Unlimited"
                      style={{ width: '100%', marginTop: 4 }}
                      value={maxPrice}
                      onChange={setMaxPrice}
                      allowClear
                      popupMatchSelectWidth={200}
                      showSearch={false}
                    >
                      {priceOptions.slice(1).map(opt => (
                        <Select.Option key={opt.value} value={opt.value}>
                          {opt.label}
                        </Select.Option>
                      ))}
                    </Select>
                  </Col>
                </Row>
              </div>
            )}
          >
            <Select.Option value="price">{getPriceLabel()}</Select.Option>
          </Select>

          {/* Reset Button */}
          {hasActiveFilters() && (
            <Button size="large" onClick={handleReset} danger>
              Reset All
            </Button>
          )}
        </Space>
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={properties}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} properties`,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          onChange={handleTableChange}
          onRow={(record) => ({
            onClick: () => router.push(`/dashboard/properties/${record.id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </div>
  )
}
