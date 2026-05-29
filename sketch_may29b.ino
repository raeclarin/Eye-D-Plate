String incomingData = "";

// Define dedicated, unchangeable pins for both actions
const int CLOSE_RELAY_PIN = 3;
const int OPEN_RELAY_PIN = 4;

void setup() {
  Serial.begin(9600);
  
  // Initialize CLOSE pin
  digitalWrite(CLOSE_RELAY_PIN, HIGH); 
  pinMode(CLOSE_RELAY_PIN, OUTPUT);

  // Initialize OPEN pin
  digitalWrite(OPEN_RELAY_PIN, HIGH); 
  pinMode(OPEN_RELAY_PIN, OUTPUT);
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n') {
      processCommand(incomingData);
      incomingData = "";  
    } else {
      incomingData += c;  
    }
  }
}

void processCommand(String command) {
  command.trim(); // Cleans up \r or spaces

  if (command == "CLOSE") {
    Serial.println("ACK: Closing Gate");
    triggerRelay(CLOSE_RELAY_PIN);
  } 
  else if (command == "OPEN") {
    Serial.println("ACK: Opening Gate");
    triggerRelay(OPEN_RELAY_PIN);
  } 
  else {
    Serial.println("ERROR: Unknown Command");
  }
}

// Reusable function to trigger a specific relay pin
void triggerRelay(int pin) {
  digitalWrite(pin, LOW);   // Relay ON
  delay(2500);              // Hold for 2.5 seconds
  digitalWrite(pin, HIGH);  // Relay OFF
}