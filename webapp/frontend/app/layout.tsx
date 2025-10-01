import './globals.css'
import 'antd/dist/reset.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import AntdRegistry from '@/components/AntdRegistry'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Cleo - Real Estate Data Platform',
  description: 'Unify Data. Unlock Deals.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AntdRegistry>
          {children}
        </AntdRegistry>
      </body>
    </html>
  )
}