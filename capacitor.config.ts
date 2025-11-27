import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.example.agriadvisor',
  appName: 'AgriAdvisor',
  webDir: 'dist',
  server: {
    androidScheme: 'http'
  }
};

export default config;