module FSM_test
  (input clk,
   input reset,
   input valid_in,
   output ready,
   output valid_out);


   enum   {IDLE, WAIT, DONE} state, nextState;

   // state register
   always @(posedge clk)
     if (reset)
       state <= IDLE;
     else
       state <= nextState;


   // next-state logic
   always_comb begin: ns
      unique case(state)
	IDLE:
	  if (valid_in)
	    nextState = WAIT;
	  else
	    nextState = IDLE;
	WAIT:
	  nextState = DONE;
	DONE:
	  nextState = IDLE;
      endcase // unique case (state)
   end // block: ns

   assign ready = state == IDLE;
   assign valid_out = state == DONE;
   

endmodule // FSM_test

