import React from 'react';
import { Button } from 'react-bootstrap';
import { LinkContainer } from 'react-router-bootstrap';

function RiderTripMedia ({ trip, driver }) {
  const photoUrl = new URL(driver.photo, process.env.REACT_APP_BASE_URL).href;

  return (
    <div className='mb-3'>
      <div className='d-flex'>
        <div className='flex-shrink-0'>
          <img
            alt={driver}
            className='rounded-circle'
            src={photoUrl}
            width={80}
            height={80}
          />
        </div>
        <div className='flex-grow-1 ms-3'>
          <h5 className='mt-0 mb-1 fw-bold'>{driver.first_name} {driver.last_name}</h5>
          <p>
            <Rating value={driver.rating} /> | <NumTrips value={driver.num_trips} /><br />
            <strong>{trip.pick_up_address}</strong> to <strong>{trip.drop_off_address}</strong><br />
            <span className='text-secondary'>{trip.status}</span>
          </p>
        </div>
      </div>
    </div>
  );
}

function Rating ({ value }) {
  return <><i className='bi bi-star-fill'></i> {value === '0' ? 'No rating' : value}</>;
}

function NumTrips ({ value }) {
  return <>{value} {value === 1 ? 'trip' : 'trips'}</>;
}

export default RiderTripMedia;
