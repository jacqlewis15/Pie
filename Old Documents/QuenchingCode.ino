#include <Wire.h>
//#include <LiquidCrystal_I2C.h>

/**********************************************************/
//LiquidCrystal_I2C lcd(0x27, 16, 2); // set the LCD address to 0x27 for a 16 chars and 2 line display
/*********************************************************/


const int analogInPin = A0;  // Analog input pin that the  is attached to
const int GasOutPin = 7; // Analog output pin that the gas solenoid is attached to
const int deltatrigger=5;
int i;
float zeropoint_float;
float sensorValue = 0;  // value read from the Omega PX138
unsigned long RunStart;
float RunAverage[10]={0,0,0,0,0,0,0,0,0,0};

const float VRefer = 3.3;       // voltage of adc reference
const int pinAdc   = A1;        // O2 Sensor
double calibration = 359; 
// 274 for frankenbox, 290 on raspi
// 262 for bulb, 271 on raspi
// 343 for ivy, 359 on raspi
// 320 for squirtle, 331 on raspi
bool hanging = false;
float O2val = 0;
String bitIn;

void setup() {
  Serial.begin(9600);
  Serial.println("Purge-o-matic!"); 
  zeropoint_float = 533;

  zeropoint_float = zeropoint_float+200;
  Serial.println(zeropoint_float); 
   pinMode(GasOutPin, OUTPUT);
   digitalWrite(GasOutPin,LOW);
  //calibration = calibrate();
  Serial.println("Calibration is:");
  Serial.println(calibration);
/*
   lcd.init();  //initialize the lcd
   lcd.backlight();  //open the backlight
*/
   
}

int calibrate() {
  
  long sum = 0;
  for(int i=0; i<64; i++)
  {
    sum += analogRead(pinAdc);
  }

  sum >>= 6;
  return sum;
  
}

void loop(void) {
  
  if (Serial.available() > 0) {
    bitIn = Serial.readString();
    if (bitIn == "wait") {
      hanging = true;
      
    }
    else if (bitIn == "go") {hanging = false;}
  }
  
  if (not hanging) {
    //Serial.println(zeropoint_float); 
    pressure_Read();
    Serial.print(sensorValue);
    Serial.print(",");
    O2val = readConcentration();
    Serial.println(O2val);
     
    if (sensorValue < zeropoint_float) {
      digitalWrite(GasOutPin,LOW); // different for single relays
      
      delay(1000);
    }
    if (sensorValue > zeropoint_float) {
      digitalWrite(GasOutPin,HIGH);
      
      delay(1000);
    }
  }
  else {
    digitalWrite(GasOutPin,HIGH);
  }

      
}

void pressure_Read(){
  long temp=0;
for (uint8_t n=0; n < 200; n++) {
    temp =  temp + analogRead(analogInPin);
  }
  sensorValue = temp/200;
  temp = 0;
}

float readO2Vout()
{
    long sum = 0;
    for(int i=0; i<64; i++)
    {
        sum += analogRead(pinAdc);
    }

    sum >>= 6;

    float MeasuredVout = sum / calibration;
    return MeasuredVout;
}

float readConcentration()
{
    // Vout samples are with reference to 3.3V
    float MeasuredVout = readO2Vout();

    //float Concentration = FmultiMap(MeasuredVout, VoutArray,O2ConArray, 6);
    //when its output voltage is 2.0V,
    float Concentration = MeasuredVout * 0.209;
    float Concentration_Percentage=Concentration*100;
    return Concentration_Percentage;
}




