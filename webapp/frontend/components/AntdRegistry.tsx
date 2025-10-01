'use client'

import React from 'react'
import { ConfigProvider } from 'antd'

export default function AntdRegistry({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#4f46e5', // Indigo-600 to match existing theme
          borderRadius: 6,
        },
      }}
    >
      {children}
    </ConfigProvider>
  )
}
