export interface CapacitorConfig {
  appId: string;
  appName: string;
  webDir: string;
  server?: {
    androidScheme?: string;
    cleartext?: boolean;
    url?: string;
    hostname?: string;
  };
  [key: string]: any;
}

const config: CapacitorConfig = {
  appId: 'com.engineering.compliancerag',
  appName: 'Compliance RAG Agent',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    cleartext: true
  }
};

export default config;
