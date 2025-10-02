'use client'

import { useState, useEffect } from 'react'
import { Table, Input, Select, Card, Typography, Space, Tag, Button, message } from 'antd'
import { SearchOutlined, EnvironmentOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
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
}

export default function PropertiesPage() {
  const router = useRouter()
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [searchText, setSearchText] = useState('')
  const [cityFilter, setCityFilter] = useState<string | undefined>(undefined)
  const [brandFilter, setBrandFilter] = useState<string | undefined>(undefined)
  const [geocodedFilter, setGeocodedFilter] = useState<string | undefined>(undefined)
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })

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

      const transformedData = (data || []).map((property: any) => ({
        ...property,
        brands: brandsByProperty.get(property.id) || []
      }))

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
    const { data, error } = await supabase
      .from('properties')
      .select('city')
      .eq('province', 'ON')
      .not('city', 'is', null)
      .order('city')

    if (data && !error) {
      const uniqueCities = Array.from(new Set(data.map(p => p.city).filter(Boolean))) as string[]
      setCities(uniqueCities)
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

  useEffect(() => {
    fetchCities()
    fetchBrands()
  }, [])

  useEffect(() => {
    fetchProperties()
  }, [pagination.current, pagination.pageSize, cityFilter, brandFilter, geocodedFilter, searchText])

  const columns: ColumnsType<Property> = [
    {
      title: 'Address',
      key: 'address',
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
      width: '45%',
    },
    {
      title: 'City',
      dataIndex: 'city',
      key: 'city',
      width: '20%',
    },
    {
      title: 'Brands',
      key: 'brands',
      width: '25%',
      render: (_, record) => {
        if (!record.brands || record.brands.length === 0) {
          return <span style={{ fontSize: '12px', color: '#8c8c8c' }}>-</span>
        }
        return (
          <Space size={[0, 4]} wrap>
            {record.brands.slice(0, 3).map((brand, idx) => (
              <Tag key={idx} color="blue" style={{ fontSize: '11px' }}>
                {brand.name}
              </Tag>
            ))}
            {record.brands.length > 3 && (
              <Tag style={{ fontSize: '11px' }}>+{record.brands.length - 3} more</Tag>
            )}
          </Space>
        )
      },
    },
    {
      title: 'Action',
      key: 'action',
      width: '10%',
      render: (_, record) => (
        <Button
          type="link"
          onClick={() => router.push(`/dashboard/properties/${record.id}`)}
        >
          View
        </Button>
      ),
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
    setGeocodedFilter(undefined)
    setPagination(prev => ({ ...prev, current: 1 }))
  }

  return (
    <div>
      <Title level={2}>
        <EnvironmentOutlined /> Properties
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space wrap>
            <Search
              placeholder="Search address, city, postal code..."
              allowClear
              enterButton={<SearchOutlined />}
              style={{ width: 350 }}
              onSearch={handleSearch}
              onChange={(e) => !e.target.value && setSearchText('')}
              value={searchText}
            />
            <Select
              placeholder="Filter by City"
              style={{ width: 180 }}
              allowClear
              value={cityFilter}
              onChange={setCityFilter}
              showSearch
            >
              {cities.map(city => (
                <Select.Option key={city} value={city}>
                  {city}
                </Select.Option>
              ))}
            </Select>
            <Select
              placeholder="Filter by Brand"
              style={{ width: 200 }}
              allowClear
              value={brandFilter}
              onChange={setBrandFilter}
              showSearch
            >
              {brands.map(brand => (
                <Select.Option key={brand} value={brand}>
                  {brand}
                </Select.Option>
              ))}
            </Select>
            <Button onClick={handleReset}>Reset Filters</Button>
          </Space>
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
