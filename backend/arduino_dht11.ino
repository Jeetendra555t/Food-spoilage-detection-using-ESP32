#include <DHT.h>

#define DHTPIN 2      // Digital pin connected to the DHT sensor
#define DHTTYPE DHT11 // DHT 11

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  Serial.println("DHT11 sensor starting...");
  
  // Initialize DHT sensor
  dht.begin();
  
  // Wait for sensor to stabilize
  delay(2000);
  
  // Test sensor
  float testTemp = dht.readTemperature();
  float testHumidity = dht.readHumidity();
  
  if (isnan(testTemp) || isnan(testHumidity)) {
    Serial.println("Failed to initialize DHT sensor!");
    Serial.println("Please check:");
    Serial.println("1. Sensor is properly connected to pin 2");
    Serial.println("2. 10K resistor is connected between VCC and DATA");
    Serial.println("3. Power supply is stable (3.3V-5.5V)");
  } else {
    Serial.println("DHT11 sensor initialized successfully!");
    Serial.print("Initial temperature: ");
    Serial.print(testTemp);
    Serial.println("°C");
    Serial.print("Initial humidity: ");
    Serial.print(testHumidity);
    Serial.println("%");
  }
}

void loop() {
  // Wait between measurements
  delay(2000);

  // Reading temperature or humidity takes about 250 milliseconds!
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  // Check if any reads failed
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
    Serial.println("Retrying in 2 seconds...");
    return;
  }

  // Create JSON string with sensor data
  String jsonData = "{";
  jsonData += "\"temperature\":" + String(temperature, 1) + ",";
  jsonData += "\"humidity\":" + String(humidity, 1);
  jsonData += "}";

  // Send data via serial
  Serial.println(jsonData);
} 