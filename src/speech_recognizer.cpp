#include <stdio.h>
#include <iostream>
#include <string.h>
#include <pocketsphinx.h>
#include <sphinxbase/ad.h>
#include <sphinxbase/err.h>
#include <yarp/dev/PolyDriver.h>
#include <yarp/dev/AudioGrabberInterfaces.h>
#include <yarp/os/Network.h>
#include <yarp/os/Port.h>
using namespace yarp::os;
using namespace yarp::sig;
using namespace yarp::dev;

const char * recognize(Network&, BufferedPort<Sound>&);

ps_decoder_t *ps;
cmd_ln_t *config;


int16 data[48005];
int16 dataResampled[48005];
uint8 utt_started, in_speech;
int32 k;
char const *hyp;
char const *decoded_speech;
Sound *s;



int main(int argc, char *argv[]) {

  config = cmd_ln_init(NULL, ps_args(), TRUE,
    "-hmm", "/usr/local/share/pocketsphinx/model/en-us/en-us",
    "-lm", "/usr/local/share/pocketsphinx/model/en-us/en-us.lm.bin",
    "-dict", "/usr/local/share/pocketsphinx/model/en-us/cmudict-en-us.dict",
    "-logfn", "/dev/null",
     NULL);

  ps = ps_init(config);

  Network yarp;
  BufferedPort<Sound> p;

  BufferedPort<Bottle> speechPort;
  speechPort.open("/speech");

  p.open("/receivewav");
  Network::connect("/MarkoAudioStream", "/receivewav");

  while(1){

    decoded_speech = recognize(yarp, p);

    Bottle& speech = speechPort.prepare();
    speech.clear();
    speech.addString(decoded_speech);

    printf("Sending %s\n", speech.toString().c_str());
    // send the message
    speechPort.write(true);

   }
}

const char * recognize(Network& yarp, BufferedPort<Sound>& p){

    ps_start_utt(ps);
    utt_started = FALSE;

    while (true) {

        s = p.read(false);
        //std::cout << "here" << std::endl;
        if (s!=NULL) {

          int num_bytes = s->getBytesPerSample();
          int num_channels = s->getChannels();
          int num_samples = s->getRawDataSize()/num_channels/num_bytes;

          for (int i=0; i<num_samples; i++)
            data[i] = s->get(i,0);



          int ind=0;

          for(int i=0; i<48000; i+=3) {
            dataResampled[ind] = data[i];
            dataResampled[ind] += data[i+1];
            dataResampled[ind] += data[i+2];
            dataResampled[ind]/=3;
            ind++;
          }
          //std::cout << ind << std::endl;

          ps_process_raw(ps, dataResampled, num_samples/3, FALSE, FALSE);

          in_speech = ps_get_in_speech(ps);
          if (in_speech && !utt_started) {
              utt_started = TRUE;
            }

          if (!in_speech && utt_started) {
              ps_end_utt(ps);
              hyp = ps_get_hyp(ps, NULL );
              return hyp;
              break;
          }
        }
    }
}
