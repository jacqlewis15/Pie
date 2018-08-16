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
double calibration; // 357 on raspberry pi, 345 on cpu

int in;
bool quenching = false;
bool hanging = false;
int O2vals[22] = {20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0};
float O2val;
int index = 0;
unsigned long start;

void setup() {
  Serial.begin(9600);
  quenching = true;
  Serial.println("Purge-o-matic!"); 
  zeropoint_float = 533;

  zeropoint_float = zeropoint_float+200;
  Serial.println(zeropoint_float); 
   pinMode(GasOutPin, OUTPUT);
   digitalWrite(GasOutPin,LOW);
  calibration = calibrate();
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
  

  pressure_Read();
  Serial.print(sensorValue);
  Serial.print(",");
  O2val = readConcentration();
  Serial.println(O2val); 
  if (hanging) {
    if ((millis()-start) > 140000) {
      hanging = false; 
      for (int i=0; i<22; i++) {
        if (O2val > O2vals[i]) {
          index = i;
          break;
        }
      }
    }
  }
  else if (quenching and (O2val < O2vals[index])) {
    start = millis();
    hanging = true;
  }
  else {
    //Serial.println(zeropoint_float); 
    if (sensorValue < zeropoint_float) {
      digitalWrite(GasOutPin,LOW);
      /*
      lcd.setCursor(0, 0); // set the cursor to column 3, line 0
      lcd.print("p: ");  // Print a message to the LCD
       lcd.setCursor(9, 0); // set the cursor to column 3, line 0
       lcd.print(" ");  // Print a message to the LCD
      lcd.setCursor(2, 0); // set the cursor to column 3, line 0
      lcd.print(sensorValue);  // Print a message to the LCD
      lcd.setCursor(10, 0); // set the cursor to column 3, line 0
      lcd.print("Open  ");  // Print a message to the LCD
      lcd.setCursor(0, 1); // set the cursor to column 3, line 0
      lcd.print("O2: ");  // Print a message to the LCD
      lcd.setCursor(4, 1); // set the cursor to column 3, line 0
      lcd.print(readConcentration());  // Print a message to the LCD 
      */ 
      delay(1000);
    }
    if (sensorValue > zeropoint_float) {
      digitalWrite(GasOutPin,HIGH);
      /*
      lcd.setCursor(0, 0); // set the cursor to column 3, line 0
      lcd.print("p: ");  // Print a message to the LCD
       lcd.setCursor(9, 0); // set the cursor to column 3, line 0
       lcd.print(" ");  // Print a message to the LCD
      lcd.setCursor(2, 0); // set the cursor to column 3, line 0
      lcd.print(sensorValue);  // Print a message to the LCD
      lcd.setCursor(10, 0); // set the cursor to column 3, line 0
      lcd.print("Closed  ");  // Print a message to the LCD
      lcd.setCursor(0, 1); // set the cursor to column 3, line 0
      lcd.print("O2: ");  // Print a message to the LCD
      lcd.setCursor(4, 1); // set the cursor to column 3, line 0
      lcd.print(readConcentration());  // Print a message to the LCD
      */  
      delay(1000);
    }
  }

      /*
      lcd.setCursor(0, 0); // set the cursor to column 3, line 0
      lcd.print("p: ");  // Print a message to the LCD
      lcd.setCursor(9, 0); // set the cursor to column 3, line 0
      lcd.print(" ");  // Print a message to the LCD
      lcd.setCursor(2, 0); // set the cursor to column 3, line 0
      lcd.print(sensorValue);  // Print a message to the LCD
      lcd.setCursor(10, 0); // set the cursor to column 3, line 0
     // lcd.print("Open  ");  // Print a message to the LCD
      lcd.setCursor(0, 1); // set the cursor to column 3, line 0
      lcd.print("O2: ");  // Print a message to the LCD
      lcd.setCursor(4, 1); // set the cursor to column 3, line 0
      lcd.print(readConcentration());  // Print a message to the LCD  
      */
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




