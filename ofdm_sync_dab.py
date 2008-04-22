# Copyright 2008 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

# ofdm_sync_dab.py - OFDM synchronisation for DAB
#
# Andreas Mueller, 2008
# andrmuel@ee.ethz.ch

from gnuradio import gr
import parameters
import sys
from math import pi

class moving_sum_ff(gr.hier_block2):
	"""
	moving sum block for float samples
	"""
	
	def __init__(self, elements, gain):
		"""
		moving sum filter, implemented with a delay line + an iir filter

		@param elements: length of the window
		@param gain: gain factor
		"""
		gr.hier_block2.__init__(self,"moving_sum",
					gr.io_signature(1, 1, gr.sizeof_float), # input signature
					gr.io_signature(1, 1, gr.sizeof_float)) # output signature

		self.input = gr.add_const_ff(0) # needed, because external inputs can only be wired to one port

		self.delay = gr.delay(gr.sizeof_float, elements-1)
		self.sub = gr.sub_ff()
		self.iir_filter = gr.iir_filter_ffd([gain],[0,1])
		
		self.connect(self, self.input, self.sub, self.iir_filter, self)
		self.connect(self.input, self.delay, (self.sub,1))

class moving_sum_cc(gr.hier_block2):
	"""
	moving sum block for complex samples
	"""
	
	def __init__(self, elements, gain):
		"""
		moving sum filter, implemented with a delay line + an iir filter

		@param elements: length of the window
		@param gain: gain factor
		"""
		gr.hier_block2.__init__(self,"moving_sum",
					gr.io_signature(1, 1, gr.sizeof_gr_complex), # input signature
					gr.io_signature(1, 1, gr.sizeof_gr_complex)) # output signature

		self.input = gr.kludge_copy(gr.sizeof_gr_complex) # needed, because external inputs can only be wired to one port

		self.delay = gr.delay(gr.sizeof_gr_complex, elements-1)
		self.sub = gr.sub_cc()
		self.iir_filter = gr.single_pole_iir_filter_cc(0.5)
		self.gain = gr.multiply_const_cc(2.*gain)
		
		self.connect(self, self.input, self.sub, self.iir_filter, self.gain, self)
		self.connect(self.input, self.delay, (self.sub,1))

class ofdm_sync_dab(gr.hier_block2):
	"""
	OFDM time and frequency synchronisation for DAB

	time synchronisation is done by using the NULL symbols
	fine frequency synchronisation is by correlating the first and the second half of the symbol
	coarse frequency synchronisation is done by moving the signal around in the frequency space
	"""
	def __init__(self,mode,debug=False):
		"""
		OFDM synchronisation for DAB

		@param mode: DAB mode (I-IV)
		@type mode: integer
		@param debug: write data streams out to files if true
		@type debug: boolean
		"""

		if mode<1 or mode>4:
			raise ValueError, "Invalid DAB mode: "+str(mode)+" (modes 1-4 exist)"

		# get the correct DAB parameters
		dp = parameters.dab_parameters(mode)
		rp = parameters.receiver_parameters(mode)
		
		gr.hier_block2.__init__(self,"ofdm_sync_dab",
		                        gr.io_signature(1, 1, gr.sizeof_gr_complex), # input signature
					gr.io_signature2(2, 2, gr.sizeof_gr_complex*dp.fft_length, gr.sizeof_char*dp.fft_length)) # output signature

		# workaround for a problem that prevents connecting more than one block directly (see trac ticket #161)
		self.input = gr.kludge_copy(gr.sizeof_gr_complex)
		self.connect(self, self.input)

		#
		# null-symbol detection
		#

		# get the magnitude squared
		self.ns_c2magsquared = gr.complex_to_mag_squared()
		
		# this wastes cpu cycles:
		# ns_detect_taps = [1]*dp.ns_length
		# self.ns_moving_sum = gr.fir_filter_fff(1,ns_detect_taps)
		# this isn't better:
		#self.ns_filter = gr.iir_filter_ffd([1]+[0]*(dp.ns_length-1)+[-1],[0,1])
		# this does the same again, but is actually faster (outsourced to an independent block ..):
		self.ns_moving_sum = moving_sum_ff(dp.ns_length,1)
		self.ns_invert = gr.multiply_const_ff(-1)

		# peak detector on the inverted, summed up signal -> we get the zeros (i.e. the position of the start of a frame)
		self.ns_peak_detect = gr.peak_detector_fb(0.6,0.7,10,0.0001) # mostly found by try and error -> remember that the values are negative!

		# connect it all
		self.connect(self.input, self.ns_c2magsquared, self.ns_moving_sum, self.ns_invert, self.ns_peak_detect, (self,1))

		if debug:
			self.connect(self.ns_invert, gr.file_sink(gr.sizeof_float, "debug/ofdm_sync_dab_ns_filter_inv_f.dat"))
			self.connect(self.ns_peak_detect,gr.file_sink(gr.sizeof_char, "debug/ofdm_sync_dab_peak_detect_b.dat"))

		#
		# fine frequency synchronisation
		#

		# the code for fine frequency synchronisation is mostly adapted
		# from ofdm_sync_pn.py - it uses frequency synchronisation as
		# described in "Robust Frequency and Timing Synchronization for
		# OFDM" by Timothy M. Schmidl and Donald C. Cox, IEEE
		# Transactions on Communications, Vol. 45, NO. 12, December
		# 1997

		# TODO gate angle calculation when unneeded (requires some conditional stream select block)

		self.ffs_delay = gr.delay(gr.sizeof_gr_complex, dp.fft_length)
		self.ffs_conj = gr.conjugate_cc()
		self.ffs_mult = gr.multiply_cc()
		#FIXME
		#self.ffs_moving_sum = moving_sum_cc(dp.fft_length/2, 2./dp.fft_length)
		self.ffs_moving_sum = gr.fir_filter_ccf(1, [1]*(dp.cp_length-rp.cp_gap))
		self.ffs_angle = gr.complex_to_arg()
		self.ffs_angle_scale = gr.multiply_const_ff(1./dp.fft_length)
		self.ffs_delay_sample_and_hold = gr.delay(gr.sizeof_char, dp.cp_length)
		self.ffs_sample_and_hold = gr.sample_and_hold_ff()
		self.ffs_nco = gr.frequency_modulator_fc(1) # ffs_sample_and_hold directly outputs phase error per sample
		self.ffs_mixer = gr.multiply_cc()

		# calculate fine frequency error
		self.connect(self.input, self.ffs_conj, self.ffs_mult)
		self.connect(self.input, self.ffs_delay, (self.ffs_mult, 1))
		self.connect(self.ffs_mult, self.ffs_moving_sum, self.ffs_angle)
		# only use the value from the first half of the first symbol
		self.connect(self.ffs_angle, self.ffs_angle_scale, (self.ffs_sample_and_hold, 0))
		self.connect(self.ns_peak_detect, self.ffs_delay_sample_and_hold, (self.ffs_sample_and_hold, 1))
		# do the correction
		self.connect(self.ffs_sample_and_hold, self.ffs_nco, (self.ffs_mixer, 0))
		self.connect(self.input, (self.ffs_mixer, 1))

		if debug:
			self.connect(self.ffs_angle, gr.file_sink(gr.sizeof_float, "debug/ofdm_sync_dab_ffs_angle.dat"))
			self.connect(self.ffs_sample_and_hold, gr.multiply_const_ff(1./(dp.T*2*pi)), gr.file_sink(gr.sizeof_float, "debug/ofdm_sync_dab_fine_freq_err_f.dat"))
			self.connect(self.ffs_mixer, gr.file_sink(gr.sizeof_gr_complex, "debug/ofdm_sync_dab_fine_freq_corrected_c.dat"))
		else: # FIXME remove this once the block is complete
			self.nop = gr.nop(gr.sizeof_gr_complex)
			self.connect(self.ffs_mixer, self.nop)
