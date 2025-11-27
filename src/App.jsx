import React, { useState, useEffect } from 'react';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  Leaf, 
  Settings, 
  RefreshCw, 
  Sun, 
  Moon, 
  Activity,
  AlertCircle,
  CheckCircle,
  Database,
  Scale,
  MapPin,
  Thermometer,
  Droplets,
  Wind,
  Eye,
  Languages
} from 'lucide-react';
import ChatBox from './components/ChatBox';
import FertilizerPesticideModal from './components/FertilizerPesticideModal';
import { apiClient } from './api/api';

const App = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);
  const [isStatusLoading, setIsStatusLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reportContent, setReportContent] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [locationError, setLocationError] = useState(null);
  const [isLocationLoading, setIsLocationLoading] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState('en'); // Default to English

  // Language options
  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'hi', label: 'Hindi' },
    { value: 'ta', label: 'Tamil' }
  ];

  useEffect(() => {
    checkSystemStatus();
    // Check status every 30 seconds
    const interval = setInterval(checkSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkSystemStatus = async () => {
    try {
      const status = await apiClient.getSystemStatus();
      setSystemStatus(status);
    } catch (error) {
      console.error('Error checking system status:', error);
      setSystemStatus({ error: 'Backend not available' });
    } finally {
      setIsStatusLoading(false);
    }
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };

  const triggerUpdate = async (updateType) => {
    try {
      await apiClient.triggerUpdate(updateType);
      // Refresh status after update
      setTimeout(checkSystemStatus, 1000);
    } catch (error) {
      console.error('Error triggering update:', error);
    }
  };

  // Function to get weather data based on GPS location
  const getWeatherByGPS = async () => {
    setIsLocationLoading(true);
    setLocationError(null);
    
    try {
      // Check if geolocation is supported
      if (!navigator.geolocation) {
        throw new Error('Geolocation is not supported by your browser');
      }
      
      // Get current position
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;
          
          try {
            // Call the actual API with lat/lon
            const weatherData = await apiClient.getWeatherByGPS(latitude, longitude);
            setWeatherData(weatherData);
          } catch (err) {
            console.error('Error fetching weather data:', err);
            setLocationError('Failed to fetch weather data: ' + err.message);
          } finally {
            setIsLocationLoading(false);
          }
        },
        (error) => {
          console.error('Error getting location:', error);
          setLocationError('Failed to get your location. Please enable location services.');
          setIsLocationLoading(false);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000
        }
      );
    } catch (err) {
      console.error('Error accessing geolocation:', err);
      setLocationError('Geolocation access denied. Please enable location services.');
      setIsLocationLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    if (status === 'connected' || status === 'initialized') {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    } else {
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
  };

  // Function to translate weather data based on selected language
  const translateWeatherData = (data, language) => {
    if (!data) return data;
    
    const translations = {
      en: {
        weather_condition: {
          "Sunny": "Sunny",
          "Cloudy": "Cloudy",
          "Rainy": "Rainy",
          "Partly Cloudy": "Partly Cloudy"
        },
        agricultural_impact: "Favorable conditions for most crops."
      },
      hi: {
        weather_condition: {
          "Sunny": "धूपवाला",
          "Cloudy": "बादलों से ढका हुआ",
          "Rainy": "बरसात का",
          "Partly Cloudy": "आंशिक रूप से बादलों से ढका हुआ"
        },
        agricultural_impact: "अधिकांश फसलों के लिए अनुकूल परिस्थितियाँ।"
      },
      ta: {
        weather_condition: {
          "Sunny": "சூரிய ஒளி",
          "Cloudy": "மேகமூட்டம்",
          "Rainy": "மழை",
          "Partly Cloudy": "பகுதியாக மேகமூட்டம்"
        },
        agricultural_impact: "பெரும்பாலான பயிர்களுக்கு ஏற்ற நிலைமைகள்."
      }
    };
    
    const langTranslations = translations[language] || translations.en;
    
    return {
      ...data,
      weather_condition: langTranslations.weather_condition[data.weather_condition] || data.weather_condition,
      agricultural_impact: langTranslations.agricultural_impact
    };
  };

  // Get translated weather data
  const translatedWeatherData = translateWeatherData(weatherData, selectedLanguage);

  return (
    <TooltipProvider>
      <div className={`min-h-screen bg-gradient-to-br from-green-50 to-blue-50 ${darkMode ? 'dark' : ''}`}>
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          {/* Changed from max-w-7xl to w-full to prevent horizontal scrolling */}
          <div className="w-full px-2 sm:px-4 md:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and Title */}
              <div className="flex items-center space-x-3">
                <div className="bg-green-600 p-2 rounded-lg">
                  <Leaf className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">Prakriti</h1>
                  <p className="text-sm text-gray-500 hidden sm:block">Agricultural AI Assistant</p>
                </div>
              </div>

              {/* Status and Actions - Responsive layout */}
              <div className="flex items-center space-x-2 sm:space-x-4">
                {/* Language Selector */}
                <div className="flex items-center space-x-1 sm:space-x-2">
                  <Languages className="w-4 h-4 text-gray-500 hidden sm:block" />
                  <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                    <SelectTrigger className="w-[80px] sm:w-[120px]">
                      <SelectValue placeholder="Language" />
                    </SelectTrigger>
                    <SelectContent>
                      {languageOptions.map((lang) => (
                        <SelectItem key={lang.value} value={lang.value}>
                          {lang.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Compare Fertilizers/Pesticides Button */}
                <Button
                  variant="outline"
                  onClick={() => setIsModalOpen(true)}
                  className="flex items-center space-x-1 sm:space-x-2 px-2 sm:px-4"
                >
                  <Scale className="w-4 h-4" />
                  <span className="hidden sm:inline">Compare Fertilizers</span>
                  <span className="sm:hidden">Compare</span>
                </Button>

                {/* System Status - Hidden on mobile, shown on larger screens */}
                <div className="hidden sm:flex items-center space-x-2">
                  {systemStatus && !isStatusLoading && (
                    <>
                      <Badge variant="outline" className="flex items-center space-x-1">
                        <Database className="w-3 h-3" />
                        <span>Neo4j</span>
                        {getStatusIcon(systemStatus.neo4j)}
                      </Badge>
                      
                      <Badge variant="outline" className="flex items-center space-x-1">
                        <Activity className="w-3 h-3" />
                        <span>Agent</span>
                        {getStatusIcon(systemStatus.agent_updater?.running ? 'connected' : 'disconnected')}
                      </Badge>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content - Changed from max-w-7xl to w-full to prevent horizontal scrolling */}
        <main className="w-full px-2 sm:px-4 py-4 sm:py-8">
          {/* System Status Alert */}
          {systemStatus?.error && (
            <Card className="mb-4 sm:mb-6 border-red-200 bg-red-50">
              <CardContent className="p-3 sm:p-4">
                <div className="flex items-center space-x-2 text-red-800">
                  <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5" />
                  <span className="font-medium text-sm sm:text-base">System Status:</span>
                  <span className="text-sm">{systemStatus.error}</span>
                </div>
                <p className="text-xs sm:text-sm text-red-600 mt-1 sm:mt-2">
                  Make sure the backend server is running on http://localhost:8000
                </p>
              </CardContent>
            </Card>
          )}

          {/* Main Interface - Responsive grid layout */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-6">
            {/* Chat Interface */}
            <div className="lg:col-span-3">
              <ChatBox 
                reportContent={reportContent}
                onReportReceived={() => setReportContent(null)}
              />
            </div>

            {/* Weather Information */}
            <div className="lg:col-span-1">
              <Card className="h-full flex flex-col">
                <CardHeader className="pb-2 sm:pb-3">
                  <CardTitle className="flex items-center space-x-2 text-base sm:text-lg">
                    <MapPin className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600" />
                    <span>Weather</span>
                  </CardTitle>
                </CardHeader>
                
                <CardContent className="flex-1 flex flex-col p-3 sm:p-4">
                  <div className="flex-1">
                    <div>
                      <h3 className="font-semibold mb-2 flex items-center text-sm sm:text-base">
                        <MapPin className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                        Weather Info
                      </h3>
                      
                      {/* Button to get weather by GPS */}
                      <div className="mb-2 sm:mb-3">
                        <Button 
                          onClick={getWeatherByGPS} 
                          disabled={isLocationLoading}
                          variant="outline" 
                          size="sm"
                          className="w-full text-xs sm:text-sm"
                        >
                          {isLocationLoading ? (
                            <>
                              <RefreshCw className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 animate-spin" />
                              <span>Getting Location...</span>
                            </>
                          ) : (
                            <>
                              <MapPin className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                              <span className="hidden xs:inline">Get Weather</span>
                              <span className="xs:hidden">Weather</span>
                            </>
                          )}
                        </Button>
                      </div>
                      
                      {/* Weather data display */}
                      {locationError && (
                        <div className="p-2 bg-red-50 text-red-700 rounded text-xs sm:text-sm mb-2 sm:mb-3">
                          {locationError}
                        </div>
                      )}
                      
                      {translatedWeatherData ? (
                        <div className="space-y-2">
                          <div className="p-2 sm:p-3 bg-blue-50 rounded-lg">
                            <div className="flex justify-between items-center mb-1 sm:mb-2">
                              <h4 className="font-medium text-sm sm:text-base">{translatedWeatherData.region}</h4>
                              <span className="text-xs sm:text-sm text-gray-500">
                                {new Date(translatedWeatherData.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                              </span>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-1 sm:gap-2">
                              <div className="flex items-center">
                                <Thermometer className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 text-red-500" />
                                <span className="text-xs sm:text-sm">
                                  {translatedWeatherData.temperature}°C
                                </span>
                              </div>
                              
                              <div className="flex items-center">
                                <Droplets className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 text-blue-500" />
                                <span className="text-xs sm:text-sm">
                                  {translatedWeatherData.humidity}%
                                </span>
                              </div>
                              
                              <div className="flex items-center">
                                <Wind className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 text-gray-500" />
                                <span className="text-xs sm:text-sm">
                                  {translatedWeatherData.wind_speed} m/s
                                </span>
                              </div>
                              
                              <div className="flex items-center">
                                <Eye className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 text-gray-500" />
                                <span className="text-xs sm:text-sm">
                                  {translatedWeatherData.pressure} hPa
                                </span>
                              </div>
                            </div>
                            
                            <div className="mt-1 sm:mt-2 pt-1 sm:pt-2 border-t border-blue-100">
                              <p className="text-xs sm:text-sm">
                                <span className="font-medium">Condition:</span> {translatedWeatherData.weather_condition}
                              </p>
                              <p className="text-xs sm:text-sm mt-1">
                                <span className="font-medium">Impact:</span> {translatedWeatherData.agricultural_impact}
                              </p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-2 sm:py-4 text-gray-500">
                          <MapPin className="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-1 sm:mb-2 text-gray-300" />
                          <p className="text-xs sm:text-sm">Click above for weather</p>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Fertilizer/Pesticide Modal */}
          <FertilizerPesticideModal
            open={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            onReportGenerated={(report) => {
              setReportContent(report);
              setIsModalOpen(false);
            }}
          />

          {/* Removed promotional sections and footer for a cleaner, professional layout */}
        </main>
      </div>
      <Toaster />
    </TooltipProvider>
  );
};

export default App;