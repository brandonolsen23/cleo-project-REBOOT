'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  Card,
  Descriptions,
  Typography,
  Space,
  Tag,
  Button,
  Spin,
  Table,
  Divider,
  Empty,
  message,
  Tabs
} from 'antd'
import {
  ArrowLeftOutlined,
  EnvironmentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DollarOutlined,
  FileTextOutlined,
  ShopOutlined
} from '@ant-design/icons'
import { supabase } from '@/lib/supabase'
import type { ColumnsType } from 'antd/es/table'

const { Title, Text } = Typography

interface Property {
  id: string
  name: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  province: string | null
  postal_code: string | null
  country: string
  address_canonical: string | null
  address_hash: string | null
  arn: string | null
  pin: string | null
  latitude: number | null
  longitude: number | null
  geocode_source: string | null
  geocode_accuracy: string | null
  created_at: string
  updated_at: string
}

interface Transaction {
  id: string
  source: string | null
  transaction_date: string | null
  transaction_type: string | null
  price: number | null
  buyer_name: string | null
  seller_name: string | null
  brokerage_name: string | null
  site_area_acres: number | null
  description: string | null
  created_at: string
}

interface Note {
  id: string
  author: string | null
  body: string
  created_at: string
}

export default function PropertyDetailPage() {
  const params = useParams()
  const router = useRouter()
  const propertyId = params.id as string

  const [property, setProperty] = useState<Property | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (propertyId) {
      fetchPropertyData()
    }
  }, [propertyId])

  const fetchPropertyData = async () => {
    setLoading(true)
    try {
      // Fetch property details
      const { data: propertyData, error: propertyError } = await supabase
        .from('properties')
        .select('*')
        .eq('id', propertyId)
        .single()

      if (propertyError) {
        message.error('Failed to load property: ' + propertyError.message)
        return
      }

      setProperty(propertyData)

      // Fetch related transactions
      const { data: transactionsData, error: transactionsError } = await supabase
        .from('transactions')
        .select('*')
        .eq('property_id', propertyId)
        .order('transaction_date', { ascending: false })

      if (!transactionsError && transactionsData) {
        setTransactions(transactionsData)
      }

      // Fetch notes
      const { data: notesData, error: notesError } = await supabase
        .from('notes')
        .select('*')
        .eq('entity_type', 'property')
        .eq('entity_id', propertyId)
        .order('created_at', { ascending: false })

      if (!notesError && notesData) {
        setNotes(notesData)
      }

    } catch (error) {
      message.error('An unexpected error occurred')
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  const transactionColumns: ColumnsType<Transaction> = [
    {
      title: 'Date',
      dataIndex: 'transaction_date',
      key: 'transaction_date',
      render: (date) => date ? new Date(date).toLocaleDateString() : 'N/A',
      width: '12%',
    },
    {
      title: 'Type',
      dataIndex: 'transaction_type',
      key: 'transaction_type',
      render: (type) => type ? <Tag>{type.toUpperCase()}</Tag> : '-',
      width: '10%',
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      render: (price) => price ? `$${price.toLocaleString()}` : '-',
      width: '15%',
    },
    {
      title: 'Buyer',
      dataIndex: 'buyer_name',
      key: 'buyer_name',
      render: (name) => name || '-',
      width: '20%',
    },
    {
      title: 'Seller',
      dataIndex: 'seller_name',
      key: 'seller_name',
      render: (name) => name || '-',
      width: '20%',
    },
    {
      title: 'Brokerage',
      dataIndex: 'brokerage_name',
      key: 'brokerage_name',
      render: (name) => name || '-',
      width: '18%',
    },
    {
      title: 'Source',
      dataIndex: 'source',
      key: 'source',
      render: (source) => source ? <Tag color="blue">{source}</Tag> : '-',
      width: '5%',
    },
  ]

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!property) {
    return (
      <Card>
        <Empty description="Property not found" />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => router.push('/dashboard/properties')}>
            Back to Properties
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push('/dashboard/properties')}
        >
          Back to Properties
        </Button>
      </Space>

      <Title level={2}>
        <EnvironmentOutlined /> Property Details
      </Title>

      {/* Property Information Card */}
      <Card title="Property Information" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="Address" span={2}>
            <Text strong>
              {property.address_canonical || property.address_line1 || 'N/A'}
            </Text>
            {property.address_line2 && (
              <>
                <br />
                <Text type="secondary">{property.address_line2}</Text>
              </>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="City">
            {property.city || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Province">
            {property.province || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Postal Code">
            {property.postal_code || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Country">
            {property.country}
          </Descriptions.Item>
          <Descriptions.Item label="ARN">
            {property.arn || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="PIN">
            {property.pin || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Geocoding Information Card */}
      <Card title="Geocoding Information" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="Status" span={2}>
            {property.latitude && property.longitude ? (
              <Tag icon={<CheckCircleOutlined />} color="success" style={{ fontSize: '14px' }}>
                Geocoded
              </Tag>
            ) : (
              <Tag icon={<CloseCircleOutlined />} color="default" style={{ fontSize: '14px' }}>
                Not Geocoded
              </Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Latitude">
            {property.latitude?.toFixed(6) || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Longitude">
            {property.longitude?.toFixed(6) || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Geocode Source">
            {property.geocode_source || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Accuracy">
            {property.geocode_accuracy || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Address Hash" span={2}>
            <Text code style={{ fontSize: '11px' }}>
              {property.address_hash || 'N/A'}
            </Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Tabs for Transactions and Notes */}
      <Card>
        <Tabs
          defaultActiveKey="transactions"
          items={[
            {
              key: 'transactions',
              label: (
                <span>
                  <DollarOutlined />
                  Transactions ({transactions.length})
                </span>
              ),
              children: (
                <>
                  {transactions.length > 0 ? (
                    <Table
                      columns={transactionColumns}
                      dataSource={transactions}
                      rowKey="id"
                      pagination={{ pageSize: 10 }}
                      expandable={{
                        expandedRowRender: (record) => (
                          <div style={{ padding: '12px' }}>
                            {record.description && (
                              <>
                                <Text strong>Description: </Text>
                                <Text>{record.description}</Text>
                                <br />
                              </>
                            )}
                            {record.site_area_acres && (
                              <>
                                <Text strong>Site Area: </Text>
                                <Text>{record.site_area_acres} acres</Text>
                              </>
                            )}
                          </div>
                        ),
                      }}
                    />
                  ) : (
                    <Empty description="No transactions found for this property" />
                  )}
                </>
              ),
            },
            {
              key: 'notes',
              label: (
                <span>
                  <FileTextOutlined />
                  Notes ({notes.length})
                </span>
              ),
              children: (
                <>
                  {notes.length > 0 ? (
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                      {notes.map((note) => (
                        <Card key={note.id} size="small">
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Text strong>{note.author || 'Anonymous'}</Text>
                              <Text type="secondary" style={{ fontSize: '12px' }}>
                                {new Date(note.created_at).toLocaleString()}
                              </Text>
                            </div>
                            <Text>{note.body}</Text>
                          </Space>
                        </Card>
                      ))}
                    </Space>
                  ) : (
                    <Empty description="No notes found for this property" />
                  )}
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* Metadata */}
      <Card size="small" style={{ marginTop: 16, background: '#fafafa' }}>
        <Space split={<Divider type="vertical" />}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            Created: {new Date(property.created_at).toLocaleString()}
          </Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            Updated: {new Date(property.updated_at).toLocaleString()}
          </Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            ID: {property.id}
          </Text>
        </Space>
      </Card>
    </div>
  )
}
