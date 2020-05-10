/**
\brief This program shows the use of the "radio" bsp module.

Since the bsp modules for different platforms have the same declaration, you
can use this project with any platform.

After loading this program, your board will switch on its radio on frequency
CHANNEL.

While receiving a packet (i.e. from the start of frame event to the end of
frame event), it will turn on its sync LED.

Every TIMER_PERIOD, it will also send a packet containing LENGTH_PACKET bytes
set to ID. While sending a packet (i.e. from the start of frame event to the
end of frame event), it will turn on its error LED.

\author Thomas Watteyne <watteyne@eecs.berkeley.edu>, August 2014.
*/

#include "board.h"
#include "radio.h"
#include "leds.h"
#include "sctimer.h"
#include "uart.h"

//=========================== defines =========================================

#define LENGTH_PACKET   125+LENGTH_CRC  ///< maximum length is 127 bytes
#define LEN_PKT_TO_SEND 4+LENGTH_CRC
#define CHANNEL         11             ///< 11=2.405GHz
#define TIMER_PERIOD    (0xffff>>4)    ///< 0xffff = 2s@32kHz
#define ID              0x99           ///< byte sent in the packets

uint8_t stringToSend[]  = "                                  \n";

//=========================== variables =======================================

enum {
    APP_FLAG_START_FRAME = 0x01,
    APP_FLAG_END_FRAME   = 0x02,
    APP_FLAG_TIMER       = 0x04,
};

typedef enum {
    APP_STATE_TX         = 0x01,
    APP_STATE_RX         = 0x02,
} app_state_t;

typedef struct {
    uint8_t              num_startFrame;
    uint8_t              num_endFrame;
    uint8_t              num_timer;
} app_dbg_t;

app_dbg_t app_dbg;

typedef struct {
    volatile    uint8_t         uartDone;
    volatile    uint8_t         uartSendNow;
                uint8_t         uart_lastTxByteIndex;

                uint8_t         flags;
                app_state_t     state;
                uint8_t         packet[LENGTH_PACKET];
                uint8_t         packet_len;
                int8_t          rxpk_rssi;
                uint8_t         rxpk_lqi;
                bool            rxpk_crc;
} app_vars_t;

app_vars_t app_vars;

//=========================== prototypes ======================================

void     cb_startFrame(PORT_TIMER_WIDTH timestamp);
void     cb_endFrame(PORT_TIMER_WIDTH timestamp);
void     cb_timer(void);

void     cb_uart_tx_done(void);
uint8_t  cb_uart_rx(void);
void    send_uart(char *msg);
void    send_uart_len(char *msg, uint8_t len);
void send_packet(void);

//=========================== main ============================================

/**
\brief The program starts executing here.
*/
int mote_main(void) {
    uint8_t i;

    uint8_t freq_offset;
    uint8_t sign;
    uint8_t read;
    char output[30];

    // clear local variables
    memset(&app_vars,0,sizeof(app_vars_t));

    // initialize board
    board_init();

    // setup UART
    uart_setCallbacks(cb_uart_tx_done,cb_uart_rx);
    uart_enableInterrupts();

    app_vars.uartDone = 1;

    // add callback functions radio
    radio_setStartFrameCb(cb_startFrame);
    radio_setEndFrameCb(cb_endFrame);

    // prepare packet
    app_vars.packet_len = sizeof(app_vars.packet);
    for (i=0;i<app_vars.packet_len;i++) {
        app_vars.packet[i] = ID;
    }

    // start bsp timer
    sctimer_set_callback(cb_timer);
    sctimer_setCompare(sctimer_readCounter()+TIMER_PERIOD);
    sctimer_enable();

    // prepare radio
    radio_rfOn();
    radio_setFrequency(CHANNEL);

    // switch in RX by default
    radio_rxEnable();
    app_vars.state = APP_STATE_RX;

    // start by a transmit
    app_vars.flags |= APP_FLAG_TIMER;
    
    while (1) {

        // sleep while waiting for at least one of the flags to be set
        while (app_vars.flags==0x00) {
            board_sleep();
        }

        // handle and clear every flag
        while (app_vars.flags) {


            //==== APP_FLAG_START_FRAME (TX or RX)

            if (app_vars.flags & APP_FLAG_START_FRAME) {
                // start of frame

                switch (app_vars.state) {
                    case APP_STATE_RX:
                        // started receiving a packet

                        // led
                        leds_error_on();
                        break;
                    case APP_STATE_TX:
                        // started sending a packet
                        //send_uart("tx start frame");

                        // led
                        leds_sync_on();
                    break;
                }

                // clear flag
                app_vars.flags &= ~APP_FLAG_START_FRAME;
            }

            //==== APP_FLAG_END_FRAME (TX or RX)

            if (app_vars.flags & APP_FLAG_END_FRAME) {
                // end of frame

                switch (app_vars.state) {

                    case APP_STATE_RX:
                        

                        // done receiving a packet
                        app_vars.packet_len = sizeof(app_vars.packet);

                        // get packet from radio
                        radio_getReceivedFrame(
                            app_vars.packet,
                            &app_vars.packet_len,
                            sizeof(app_vars.packet),
                            &app_vars.rxpk_rssi,
                            &app_vars.rxpk_lqi,
                            &app_vars.rxpk_crc
                        );

                        freq_offset = radio_getFrequencyOffset();
                        sign = (freq_offset & 0x80) >> 7;
                        if (sign){
                            read = 0xff - (uint8_t)(freq_offset) + 1;
                        } else {
                            read = freq_offset;
                        }

                        for (i = 0; i < 20; i++) {
                            output[i] = ' ';
                        }
                        output[i++] = (app_vars.packet_len / 10) + '0';
                        output[i++] = (app_vars.packet_len % 10) + '0';



                        //send_uart_len(output, 30);

                        app_vars.state = APP_STATE_TX;
                        send_uart("received!");
                        send_uart("tx continuous");
                        radio_rfOff();

                        // led
                        leds_error_off();
                        break;
                    case APP_STATE_TX:
                        // done sending a packet

                        // switch to RX mode
                        //radio_rxEnable();
                        //app_vars.state = APP_STATE_RX;
                        send_packet();

                        // led
                        leds_sync_off();
                        break;
                }
                // clear flag
                app_vars.flags &= ~APP_FLAG_END_FRAME;
            }

            //==== APP_FLAG_TIMER

            if (app_vars.flags & APP_FLAG_TIMER) {
                // timer fired

                if (app_vars.state==APP_STATE_RX) {
                    send_uart("rx waiting");
                    radio_rxNow();
                }

                if (app_vars.state==APP_STATE_TX) {
                    send_packet();

                    
                }

                // clear flag
                app_vars.flags &= ~APP_FLAG_TIMER;
            }
        }
    }
}

void send_packet() {
    int i;
    // prepare packet
    app_vars.packet_len = sizeof(app_vars.packet);
    i = 0;
    app_vars.packet[i++] = 5;
    app_vars.packet[i++] = 23;
    app_vars.packet[i++] = 15;
    app_vars.packet[i++] = 9;
    app_vars.packet[i++] = CHANNEL;
    while (i<app_vars.packet_len) {
        app_vars.packet[i++] = ID;
    }

    // start transmitting packet
    radio_loadPacket(app_vars.packet,LEN_PKT_TO_SEND);
    radio_txEnable();
    radio_txNow();

}

void send_uart(char *msg) {
    send_uart_len(msg, strlen(msg));
}

void send_uart_len(char *msg, uint8_t len) {
    uint8_t i;
    uint8_t smaller_len = len < sizeof(stringToSend) ? len : sizeof(stringToSend);    

    while (app_vars.uartDone == 0);

    for (i = 0; i < sizeof(stringToSend); i++) {
        stringToSend[i] = ' ';
    }

    for (i = 0; i < strlen(msg); i++) {
        stringToSend[i] = msg[i];
    }


    stringToSend[sizeof(stringToSend)-2] = '\r';
    stringToSend[sizeof(stringToSend)-1] = '\n';

    app_vars.uartDone              = 0;
    app_vars.uart_lastTxByteIndex  = 0;
    uart_writeByte(stringToSend[app_vars.uart_lastTxByteIndex]);
}

//=========================== callbacks =======================================

void cb_startFrame(PORT_TIMER_WIDTH timestamp) {
    // set flag
    app_vars.flags |= APP_FLAG_START_FRAME;

    // update debug stats
    app_dbg.num_startFrame++;
}

void cb_endFrame(PORT_TIMER_WIDTH timestamp) {
    // set flag
    app_vars.flags |= APP_FLAG_END_FRAME;

    // update debug stats
    app_dbg.num_endFrame++;
}

void cb_timer(void) {
    // set flag
    app_vars.flags |= APP_FLAG_TIMER;

    // update debug stats
    app_dbg.num_timer++;

    sctimer_setCompare(sctimer_readCounter()+TIMER_PERIOD);
}

void cb_uart_tx_done(void) {
    app_vars.uart_lastTxByteIndex++;
    if (app_vars.uart_lastTxByteIndex<sizeof(stringToSend)) {
        uart_writeByte(stringToSend[app_vars.uart_lastTxByteIndex]);
    } else {
        app_vars.uartDone = 1;
    }
}

uint8_t cb_uart_rx(void) {
    uint8_t byte;

    // toggle LED
    leds_error_toggle();

    // read received byte
    byte = uart_readByte();

    // echo that byte over serial
    uart_writeByte(byte);

    return 0;
}
