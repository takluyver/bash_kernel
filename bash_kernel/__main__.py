from ipykernel.kernelapp import IPKernelApp
from .kernel import BashKernel
IPKernelApp.launch_instance(kernel_class=BashKernel)
