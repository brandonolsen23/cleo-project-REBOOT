import { createServerSupabase } from '@/lib/supabase'
import { UserProfile } from '@/lib/auth'

export default async function DashboardPage() {
  const supabase = createServerSupabase()

  const {
    data: { session },
  } = await supabase.auth.getSession()

  let profile: UserProfile | null = null

  if (session?.user) {
    const { data } = await supabase
      .from('user_profiles')
      .select('*')
      .eq('id', session.user.id)
      .single()

    profile = data
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Welcome</h3>
          <p className="text-gray-600">
            {profile?.full_name || session?.user.email}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Role: {profile?.role}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Quick Actions</h3>
          <div className="space-y-2">
            <a
              href="/dashboard/properties"
              className="block text-indigo-600 hover:text-indigo-800"
            >
              View Properties
            </a>
            <a
              href="/dashboard/transactions"
              className="block text-indigo-600 hover:text-indigo-800"
            >
              View Transactions
            </a>
            {profile?.role === 'admin' && (
              <a
                href="/admin/users"
                className="block text-indigo-600 hover:text-indigo-800"
              >
                Manage Users
              </a>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">System Status</h3>
          <div className="flex items-center text-green-600">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            All systems operational
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Recent Activity</h2>
        </div>
        <div className="p-6">
          <p className="text-gray-500">No recent activity to display.</p>
        </div>
      </div>
    </div>
  )
}