'use client'

import { useState, useEffect } from 'react'
import { createClientSupabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { UserProfile, roleLabels } from '@/lib/auth'
import { useRouter } from 'next/navigation'

interface UserMenuProps {
  user: User
}

export default function UserMenu({ user }: UserMenuProps) {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [isOpen, setIsOpen] = useState(false)
  const router = useRouter()
  const supabase = createClientSupabase()

  useEffect(() => {
    async function fetchProfile() {
      try {
        const { data, error } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('id', user.id)
          .single()

        if (error) {
          console.error('Error fetching profile:', error)
        } else {
          setProfile(data)
        }
      } catch (err) {
        console.error('Error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchProfile()
  }, [user.id, supabase])

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    router.push('/login')
    router.refresh()
  }

  if (loading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
        <div className="w-20 h-4 bg-gray-200 rounded animate-pulse"></div>
      </div>
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 text-gray-700 hover:text-gray-900 focus:outline-none"
      >
        <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
          {profile?.full_name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase()}
        </div>
        <span className="text-sm font-medium">
          {profile?.full_name || user.email}
        </span>
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 border">
          <div className="px-4 py-2 text-sm text-gray-700 border-b">
            <div className="font-medium">{profile?.full_name || user.email}</div>
            <div className="text-xs text-gray-500">
              {profile?.role && roleLabels[profile.role as keyof typeof roleLabels]}
            </div>
          </div>

          <button
            onClick={() => {
              setIsOpen(false)
              router.push('/profile')
            }}
            className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Profile Settings
          </button>

          {profile?.role === 'admin' && (
            <button
              onClick={() => {
                setIsOpen(false)
                router.push('/admin/users')
              }}
              className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              User Management
            </button>
          )}

          <button
            onClick={handleSignOut}
            className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
          >
            Sign Out
          </button>
        </div>
      )}
    </div>
  )
}