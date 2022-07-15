import React, { useEffect, useState } from 'react';
import { Formik } from 'formik';
import { DateTime } from 'luxon';
import { Button, Form, Modal, Spinner } from 'react-bootstrap';
import { LinkContainer } from 'react-router-bootstrap';

import RiderTripMedia from './RiderTripMedia';
import { rateTrip } from '../services/TripService';
import { getDriver } from '../services/UserService';

function TripMedia ({ trip, group, otherGroup }) {
  const user = trip[otherGroup];
  const photoUrl = new URL(user.photo, process.env.REACT_APP_BASE_URL).href;
  const href = group ? `/${group}/${trip.id}` : undefined;
  const created = DateTime.fromISO(trip.created).toLocaleString(DateTime.DATETIME_MED);

  return (
    <div className='mb-3'>
      <div className='d-flex'>
        <div className='flex-shrink-0'>
          <img
            alt={user}
            className='rounded-circle'
            src={photoUrl}
            width={80}
            height={80}
          />
        </div>
        <div className='flex-grow-1 ms-3'>
          <h5 className='mt-0 mb-1 fw-bold'>{user.first_name} {user.last_name}</h5>
          <p>
            <strong>{trip.pick_up_address}</strong> to <strong>{trip.drop_off_address}</strong><br />
            <span>{created}</span><br />
            <span className='text-secondary'>{trip.status}</span>
          </p>
        </div>
      </div>
      {
        href && (
          <div className='d-grid'>
            <LinkContainer to={href}>
              <Button variant='primary'>Detail</Button>
            </LinkContainer>
          </div>
        )
      }
      {
        !href && trip.status === 'COMPLETED' && otherGroup === 'driver' && (
          <div className='d-grid'>
            <RatingButton trip={trip} />
          </div>
        )
      }
    </div>
  );
}

function RatingButton ({ trip }) {
  const [driver, setDriver] = useState(null);
  const [rating, setRating] = useState(trip.rating);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const loadDriver = async (id) => {
      const { response, isError } = await getDriver(id);
      if (isError) {
        setDriver(null);
      } else {
        setDriver(response.data);
      }
    };
    loadDriver(trip.driver.id);
  }, [trip]);

  const onSubmit = async (values, actions) => {
    try {
      const { response, isError } = await rateTrip(
        trip.id,
        values.rating,
      );
      if (isError) {
        const data = response.response.data;
        for (const value in data) {
          actions.setFieldError(value, data[value].join(' '));
        }
      } else {
        setRating(values.rating);
        setShowModal(false);
      }
    } catch (error) {
      console.error(error);
    }
  };

  if (driver === null) {
    return (
      <div className='d-flex justify-content-center'>
        <Spinner animation='border' />
      </div>
    );
  }

  return (
    <>
      {
        rating === null ? (
          <div className='d-grid'>
            <Button variant='primary' onClick={() => setShowModal(true)}>Rate</Button>
          </div>
        ) : (
          <div className='d-grid'>
            <Button disabled={true} variant='primary'>You rated {rating} stars</Button>
          </div>
        )
      }
      <Modal backdrop='static' keyboard={false} onHide={() => setShowModal(false)} show={showModal}>
        <Modal.Header closeButton>
          <Modal.Title>How was your trip with {driver.first_name} {driver.last_name}?</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <>
            <RiderTripMedia trip={trip} driver={driver} />
            <Formik
              initialValues={{
                rating: 5,
              }}
              onSubmit={onSubmit}
            >
              {({
                errors, 
                handleChange,
                handleSubmit,
                isSubmitting,
                values,
              }) => (
                <Form noValidate onSubmit={handleSubmit}>
                  <Form.Group className='mb-3' controlId='rating'>
                    <Form.Label>Rating:</Form.Label>
                    <Form.Control
                      className={'rating' in errors ? 'is-invalid' : ''}
                      max={5}
                      min={1}
                      name='rating'
                      onChange={handleChange}
                      required
                      step={1}
                      type='number'
                      value={values.rating}
                    />
                    {
                      'rating' in errors && (
                        <Form.Control.Feedback type='invalid'>{errors.rating}</Form.Control.Feedback>
                      )
                    }
                  </Form.Group>
                  <div className='d-grid mb-3'>
                    <Button disabled={isSubmitting} type='submit' variant='primary'>Submit</Button>
                  </div>
                </Form>
              )}
            </Formik>
          </>
        </Modal.Body>
      </Modal>
    </>
  );
}

export default TripMedia;
