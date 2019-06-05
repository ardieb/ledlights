#include <AlaLedRgb.h>
#include <MemoryFree.h>
#include <stdlib.h>

#define DATA_PIN 6    // WS2811 control connected to pin 6
#define NUM_PIXELS 240 // number of leds in the LED strip
#define CMDBUFSIZE 16   // buffer size for receiving serial commands

AlaLedRgb rgbStrip;
char cmdBuffer[CMDBUFSIZE];

// global settings and initial values
int animation = ALA_OFF;
AlaColor color = 0xdddddd;
AlaColor white = 0xffffff;
AlaPalette palette = alaPalNull;
int paletteId=0;
float brightness = 1;
long duration = 66;
int charsRead = 0;
bool runAnim = true;

void(*recover)(void) = 0;

void setup()
{
  rgbStrip.initWS2812(NUM_PIXELS, DATA_PIN);
  rgbStrip.setBrightness(color.scale(brightness));
  rgbStrip.setAnimation(animation, duration, color);
  Serial.begin(9600);
}

void loop()
{
  if (Serial.available())
  {
    runAnim = true;
    charsRead = Serial.readBytesUntil('\n', cmdBuffer, sizeof(cmdBuffer) - 1);  //read entire line
    cmdBuffer[charsRead] = '\0';       // Make it a C string
    Serial.print(">"); Serial.println(cmdBuffer);
    
    if(cmdBuffer[1] != '=' || strlen(cmdBuffer)<3)
    {
      Serial.println("KO");
      recover();
    }
    else
    {
      switch(toupper(cmdBuffer[0]))
      {
      //case 'S':
      //  for (int i = 3; i < charsRead; i += 7) { // 7 chars is the size of a rgb color hex eg. #FFFFFF
      //    color = strtol(&cmdBuffer[i],0,16);
      //    rgbStrip->leds[i/6] = color;
      //  }
      //  runAnim = false;
      // break;
      case 'I':
        animation = ALA_ON;
        color = strtol(&cmdBuffer[2],0,16);
        palette=alaPalNull;
        duration = 66;
        rgbStrip.setBrightness(white.scale(1.0));
        break;
      case 'A':
        animation = atoi(&cmdBuffer[2]);
        break;
      case 'B':
        brightness = atoi(&cmdBuffer[2]);
        rgbStrip.setBrightness(white.scale((float)brightness / 100));
        break;
      case 'C':
        color = strtol(&cmdBuffer[2], 0, 16);
        palette=alaPalNull;
        break;
      case 'D':
        duration = atol(&cmdBuffer[2]);
        break;
      case 'P':
        paletteId = atoi(&cmdBuffer[2]);
        switch(paletteId)
        {
        case 0:
          palette=alaPalNull;
          break;
        case 1:
          palette=alaPalRgb;
          break;
        case 2:
          palette=alaPalRainbow;
          break;
        case 3:
          palette=alaPalParty;
          break;
        case 4:
          palette=alaPalHeat;
          break;
        case 5:
          palette=alaPalFire;
          break;
        case 6:
          palette=alaPalCool;
          break;
        }
        break;
      
      default:
        Serial.println("KO");
      }
    }
    if(palette==alaPalNull) {
        rgbStrip.setAnimation(animation, duration, color);
      }
    else {
        rgbStrip.setAnimation(animation, duration, palette);
      }
    if(runAnim)
        rgbStrip.runAnimation();
    Serial.println(freeMemory());
  }
}
