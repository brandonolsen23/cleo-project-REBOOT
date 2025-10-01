'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClientSupabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { UserProfile, UserRole, hasPermission } from '@/lib/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: UserRole
  redirectTo?: string
}

export default function ProtectedRoute({
  children,
  requiredRole = 'viewer',
  redirectTo = '/login'
}: ProtectedRouteProps) {
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [authorized, setAuthorized] = useState(false)
  const router = useRouter()
  const supabase = createClientSupabase()

  useEffect(() => {
    async function checkAuth() {
      try {
        // Get current session
        const { data: { session } } = await supabase.auth.getSession()

        if (!session?.user) {
          router.push(redirectTo)
          return
        }

        setUser(session.user)

        // Get user profile for role checking
        const { data: profileData, error } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('id', session.user.id)
          .single()

        if (error) {
          console.error('Error fetching profile:', error)
          router.push('/unauthorized')
          return
        }

        setProfile(profileData)

        // Check if user has required role
        const userRole = profileData.role as UserRole
        if (hasPermission(userRole, requiredRole)) {
          setAuthorized(true)
        } else {
          router.push('/unauthorized')
        }
      } catch (err) {
        console.error('Auth check error:', err)
        router.push(redirectTo)
      } finally {
        setLoading(false)
      }
    }

    checkAuth()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_OUT' || !session) {
          router.push(redirectTo)
        } else if (event === 'SIGNED_IN' && session?.user) {
          setUser(session.user)
          // Re-check authorization when user signs in
          checkAuth()
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [supabase, router, redirectTo, requiredRole])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!authorized) {
    return null // Will redirect to unauthorized or login
  }

  return <>{children}</>
}

// HOC version for easier use
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  requiredRole?: UserRole
) {
  return function AuthenticatedComponent(props: P) {
    return (
      <ProtectedRoute requiredRole={requiredRole}>
        <Component {...props} />
      </ProtectedRoute>
    )
  }
}