import RPi.GPIO as GPIO


class PowerManager(object):
    def __init__(self, pin_sign: int, pin_lights: int):
        GPIO.setmode(GPIO.BOARD)
        self.pins = {
            'sign': pin_sign,
            'lights': pin_lights
        }

        # Configure the pins as outputs
        GPIO.setup(pin_sign, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(pin_lights, GPIO.OUT, initial=GPIO.LOW)

    def lights(self, status: bool):
        self._write_pin(self.pins['lights'], status)

    def sign(self, status: bool):
        self._write_pin(self.pins['sign'], status)

    @staticmethod
    def _write_pin(pin: int, status: bool):
        GPIO.output(pin, 1 if status else 0)
