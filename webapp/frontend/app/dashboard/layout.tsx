'use client'

import { Layout } from 'antd'

const { Header, Content } = Layout

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        display: 'flex',
        alignItems: 'center',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        padding: '0 50px'
      }}>
        <h1 style={{
          fontSize: '24px',
          fontWeight: 'bold',
          color: '#4f46e5',
          margin: 0
        }}>
          Cleo
        </h1>
        <span style={{
          marginLeft: '12px',
          fontSize: '14px',
          color: '#8c8c8c'
        }}>
          Real Estate Data Platform
        </span>
      </Header>
      <Content style={{ padding: '24px 50px' }}>
        {children}
      </Content>
    </Layout>
  )
}