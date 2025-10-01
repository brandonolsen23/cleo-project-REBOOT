'use client'

import { Card, Col, Row, Typography, Badge } from 'antd'
import { HomeOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons'
import Link from 'next/link'

const { Title, Text, Paragraph } = Typography

export default function DashboardPage() {
  return (
    <div>
      <Title level={2}>Dashboard</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={24} md={8}>
          <Card>
            <Title level={4}>Welcome</Title>
            <Paragraph>
              Cleo Real Estate Platform
            </Paragraph>
          </Card>
        </Col>

        <Col xs={24} sm={24} md={8}>
          <Card title="Quick Actions">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <Link href="/dashboard/properties" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <HomeOutlined />
                <Text>View Properties</Text>
              </Link>
              <Link href="/dashboard/transactions" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileTextOutlined />
                <Text>View Transactions</Text>
              </Link>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={24} md={8}>
          <Card title="System Status">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Badge status="success" />
              <Text type="success">All systems operational</Text>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="Recent Activity">
        <Text type="secondary">No recent activity to display.</Text>
      </Card>
    </div>
  )
}