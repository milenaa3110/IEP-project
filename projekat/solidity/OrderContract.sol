pragma solidity ^0.8.0;

contract OrderContract {
    event LogError(string reason);
    enum OrderStatus { Created, Paid, InDelivery, Delivered }
    OrderStatus public status = OrderStatus.Created;

    address payable public owner;   // Owner of the store
    address payable public customer; // Customer who created the order
    address payable public courier;  // Courier delivering the order

    uint public orderPrice; // Price of the order in wei

    constructor(address payable _customer, uint _orderPrice) {
        owner = payable(msg.sender);
        customer = _customer;
        orderPrice = _orderPrice;
    }

    function setCourier(address payable _courier) public {
        require(msg.sender == owner, "Only the owner can set the courier.");
        if (courier != address(0)) {
            emit LogError("Courier is already set.");
            return;
        }
        require(courier == address(0), "Courier is already set.");
        courier = _courier;
        status = OrderStatus.InDelivery;
    }

    function makePayment() public payable {
        status = OrderStatus.Paid;
    }


    function confirmDelivery() public {
        require(msg.sender == customer, "Invalid customer account.");
        require(status != OrderStatus.Created, "Transfer not complete.");
        require(courier != address(0), "Delivery not complete.");

        status = OrderStatus.Delivered;
        uint ownerPayment = (orderPrice * 80) / 100;
        uint courierPayment = orderPrice - ownerPayment;

        owner.transfer(ownerPayment);
        courier.transfer(courierPayment);
    }

    function forbiddenInteraction() public view {
        require(status != OrderStatus.Delivered, "No further interactions are allowed with this contract.");
    }


}
