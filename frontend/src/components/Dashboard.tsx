import React, { useEffect, useState } from "react";
import { RevenueSummary } from "./RevenueSummary";
import { useAuth } from "../contexts/AuthContext.new";
import { SecureAPI } from "../lib/secureApi";

interface PropertyOption {
  id: string;
  name: string;
}

const Dashboard: React.FC = () => {
  const { user, isLoading: authLoading, isAuthenticated } = useAuth();
  const tenantId = user?.tenant_id || user?.app_metadata?.tenant_id || user?.user_metadata?.tenant_id || null;
  const [properties, setProperties] = useState<PropertyOption[]>([]);
  const [propertiesTenantId, setPropertiesTenantId] = useState<string | null>(null);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [propertiesLoading, setPropertiesLoading] = useState(true);
  const [propertiesError, setPropertiesError] = useState('');
  const [reloadProperties, setReloadProperties] = useState(0);
  const now = new Date();
  const [selectedMonth, setSelectedMonth] = useState(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  );
  const [year, month] = selectedMonth.split('-').map(Number);

  useEffect(() => {
    let cancelled = false;
    setProperties([]);
    setPropertiesTenantId(null);
    setSelectedProperty('');
    setPropertiesError('');

    if (authLoading) {
      setPropertiesLoading(true);
      return () => { cancelled = true; };
    }
    if (!isAuthenticated || !tenantId) {
      setPropertiesLoading(false);
      setPropertiesError('An authenticated tenant is required to load properties.');
      return () => { cancelled = true; };
    }

    setPropertiesLoading(true);
    SecureAPI.getDashboardProperties()
      .then((response) => {
        if (cancelled) return;
        const tenantProperties = Array.isArray(response?.properties) ? response.properties : [];
        setProperties(tenantProperties);
        setPropertiesTenantId(tenantId);
        setSelectedProperty(tenantProperties[0]?.id || '');
      })
      .catch(() => {
        if (!cancelled) setPropertiesError('Could not load properties. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setPropertiesLoading(false);
      });

    return () => { cancelled = true; };
  }, [authLoading, isAuthenticated, user?.id, tenantId, reloadProperties]);
  const visibleProperties = propertiesTenantId === tenantId ? properties : [];
  const visibleSelectedProperty = propertiesTenantId === tenantId ? selectedProperty : '';

  return (
    <div className="p-4 lg:p-6 min-h-full">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-900">Property Management Dashboard</h1>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 lg:p-6">
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
              <div>
                <h2 className="text-lg lg:text-xl font-medium text-gray-900 mb-2">Revenue Overview</h2>
                <p className="text-sm lg:text-base text-gray-600">
                  Monthly performance insights for your properties
                </p>
              </div>
              
              <div className="flex flex-col sm:items-end gap-3">
                <div className="flex flex-col sm:items-end">
                  <label htmlFor="dashboard-month" className="text-xs font-medium text-gray-700 mb-1">Reporting month</label>
                  <input
                    id="dashboard-month"
                    type="month"
                    value={selectedMonth}
                    onChange={(e) => setSelectedMonth(e.target.value)}
                    className="block w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
                <div className="flex flex-col sm:items-end">
                  <label htmlFor="dashboard-property" className="text-xs font-medium text-gray-700 mb-1">Select Property</label>
                  <select
                    id="dashboard-property"
                    value={visibleSelectedProperty}
                    onChange={(e) => setSelectedProperty(e.target.value)}
                    disabled={propertiesLoading || visibleProperties.length === 0}
                    className="block w-full sm:w-auto min-w-[200px] px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  >
                    {visibleProperties.map((property) => (
                      <option key={property.id} value={property.id}>
                        {property.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {propertiesLoading && <p role="status" className="text-sm text-gray-600">Loading properties…</p>}
            {!propertiesLoading && propertiesError && (
              <div role="alert" className="flex items-center gap-3 text-sm text-red-700">
                <span>{propertiesError}</span>
                {isAuthenticated && tenantId && (
                  <button type="button" className="underline" onClick={() => setReloadProperties((value) => value + 1)}>
                    Retry
                  </button>
                )}
              </div>
            )}
            {!propertiesLoading && !propertiesError && visibleProperties.length === 0 && (
              <p className="text-sm text-gray-600">No properties are available for this account.</p>
            )}
            {!propertiesLoading && !propertiesError && visibleSelectedProperty && (
              <RevenueSummary propertyId={visibleSelectedProperty} month={month} year={year} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
