module Iface_test
  (input clk,
   input reset,
   input data_in,
   input valid_in,
   output data_out,
   output valid_out);


   wire   fsm0_valid;
   wire [utils::clog2(depth+1)-1:0] cap;

   wire full, empty, enq, deq;
   wire ready0, ready1;
   
   FSM_test fsm0(.clk(clk), 
		 .reset(reset), 
		 .valid_in(valid_in),
		 .ready(ready0),
		 .valid_out(fsm0_valid));

   assign enq = fsm0_valid;
   assign deq = ready1;

   CapQueue #(.width(WIDTH), .depth(DEPTH)) q 
     (.clk(clk), 
      .reset(reset),
      .enq(enq),
      .deq(deq),
      .i(data_in),
      .full(full),
      .empty(empty),
      .o(data_out),
      .capacity(cap));
     

   FSM_test fsm1(.clk(clk),
		 .reset(reset),
		 .valid_in(fsm0_valid),
		 .ready(ready1),
		 .valid_out(valid_out));
   

endmodule // Iface_test
