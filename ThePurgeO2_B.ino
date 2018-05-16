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




void setup() {
  Serial.begin(9600);
  Serial.println("Purge-o-matic!"); 
  zeropoint_float = 533;

  zeropoint_float = zeropoint_float+200;
  Serial.println(zeropoint_float); 
   pinMode(GasOutPin, OUTPUT);
   digitalWrite(GasOutPin,LOW);
/*
   lcd.init();  //initialize the lcd
   lcd.backlight();  //open the backlight
*/
   
}


void loop(void) {
  

  pressure_Read();
  Serial.print(sensorValue);
  Serial.print(",");
  Serial.println(readConcentration()); 
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

    float MeasuredVout = sum * (VRefer / 1023.0);
    return MeasuredVout;
}

float readConcentration()
{
    // Vout samples are with reference to 3.3V
    float MeasuredVout = readO2Vout();

    //float Concentration = FmultiMap(MeasuredVout, VoutArray,O2ConArray, 6);
    //when its output voltage is 2.0V,
    float Concentration = MeasuredVout * 0.239;
    float Concentration_Percentage=Concentration*100;
    return Concentration_Percentage;
}




