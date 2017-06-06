/* -*- c++ -*- */
/* 
 * Copyright 2017 Moritz Luca Schmid, Communications Engineering Lab (CEL) / Karlsruhe Institute of Technology (KIT).
 * 
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 * 
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifndef INCLUDED_DAB_TRANSMISSION_FRAME_MUX_BB_IMPL_H
#define INCLUDED_DAB_TRANSMISSION_FRAME_MUX_BB_IMPL_H

#include <dab/transmission_frame_mux_bb.h>

namespace gr {
  namespace dab {

    class transmission_frame_mux_bb_impl : public transmission_frame_mux_bb
    {
     private:
      int d_transmission_mode;
      std::vector<unsigned int> d_subch_size;

      const unsigned int d_fib_len = 32; // length of a fib in bytes
      const unsigned int d_cif_len = 6912; // length of a cif in bytes
      const unsigned int d_cu_len = 8; // length of a capacity unit in bytes
      unsigned int d_vlen_out, d_num_cifs, d_num_fibs, d_subch_total_len;

     public:
      transmission_frame_mux_bb_impl(int transmission_mode, const std::vector<unsigned int> &subch_size);
      ~transmission_frame_mux_bb_impl();

      // Where all the action really happens
      void forecast (int noutput_items, gr_vector_int &ninput_items_required);

      int general_work(int noutput_items,
           gr_vector_int &ninput_items,
           gr_vector_const_void_star &input_items,
           gr_vector_void_star &output_items);
    };

  } // namespace dab
} // namespace gr

#endif /* INCLUDED_DAB_TRANSMISSION_FRAME_MUX_BB_IMPL_H */

