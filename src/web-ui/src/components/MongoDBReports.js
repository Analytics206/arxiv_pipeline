import React, { useState, useEffect } from 'react';
import { getPaperAnalysisByTime } from '../services/DatabaseMetricsService';
import { Card, Container, Row, Col, Form, Button, Spinner } from 'react-bootstrap';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import '../styles/PlaceholderPage.css';
import '../styles/Dashboard.css';

function MongoDBReports() {
  const [paperAnalysis, setPaperAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [category, setCategory] = useState('');
  const [availableCategories, setAvailableCategories] = useState([]);
  const [activeView, setActiveView] = useState('yearly'); // 'yearly', 'monthly', or 'daily'
  
  // Fetch paper analysis data on component mount
  useEffect(() => {
    fetchPaperAnalysisData();
  }, []);
  
  // Function to fetch paper analysis data with optional filters
  const fetchPaperAnalysisData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPaperAnalysisByTime(
        startDate || null,
        endDate || null,
        yearFilter || null,
        category || null
      );
      setPaperAnalysis(data);
      // Store available categories if returned and not already set
      if (data.categories && data.categories.length > 0) {
        setAvailableCategories(data.categories);
      }
    } catch (err) {
      console.error('Error fetching paper analysis data:', err);
      setError('Failed to load paper analysis data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  // Function to handle filter form submission
  const handleFilterSubmit = (e) => {
    e.preventDefault();
    fetchPaperAnalysisData();
  };
  
  // Function to clear all filters
  const clearFilters = () => {
    setStartDate('');
    setEndDate('');
    setYearFilter('');
    setCategory('');
    // Fetch data without filters
    getPaperAnalysisByTime().then(data => {
      setPaperAnalysis(data);
      if (data.categories && data.categories.length > 0) {
        setAvailableCategories(data.categories);
      }
    });
  };
  
  // Function to transform yearly data for charts
  const prepareYearlyChartData = () => {
    if (!paperAnalysis || !paperAnalysis.yearly) return [];
    
    return Object.entries(paperAnalysis.yearly).map(([year, count]) => ({
      name: year,
      papers: count
    }));
  };
  
  // Function to transform monthly data for charts
  const prepareMonthlyChartData = () => {
    if (!paperAnalysis || !paperAnalysis.monthly) return [];
    
    return Object.entries(paperAnalysis.monthly).map(([yearMonth, count]) => {
      // Format the year-month (e.g., "2023-01" to "Jan 2023")
      const [year, month] = yearMonth.split('-');
      const date = new Date(year, parseInt(month) - 1, 1);
      const formattedMonth = date.toLocaleString('default', { month: 'short' });
      
      return {
        name: `${formattedMonth} ${year}`,
        papers: count,
        yearMonth: yearMonth // Keep original for sorting
      };
    }).sort((a, b) => a.yearMonth.localeCompare(b.yearMonth));
  };
  
  // Function to transform daily data for charts
  const prepareDailyChartData = () => {
    if (!paperAnalysis || !paperAnalysis.daily) return [];
    
    return Object.entries(paperAnalysis.daily).map(([date, count]) => {
      // Format the date (e.g., "2023-01-15" to "Jan 15, 2023")
      const [year, month, day] = date.split('-');
      const dateObj = new Date(year, parseInt(month) - 1, parseInt(day));
      const formattedDate = dateObj.toLocaleString('default', { 
        month: 'short',
        day: 'numeric'
      });
      
      return {
        name: formattedDate,
        papers: count,
        fullDate: date // Keep original for sorting
      };
    }).sort((a, b) => a.fullDate.localeCompare(b.fullDate));
  };
  
  // Prepare data based on active view
  const getChartData = () => {
    switch (activeView) {
      case 'yearly':
        return prepareYearlyChartData();
      case 'monthly':
        return prepareMonthlyChartData();
      case 'daily':
        return prepareDailyChartData();
      default:
        return [];
    }
  };
  
  // Determine chart labels based on active view
  const getChartLabel = () => {
    switch (activeView) {
      case 'yearly':
        return 'Papers Published by Year';
      case 'monthly':
        return 'Papers Published by Month';
      case 'daily':
        return 'Papers Published by Day';
      default:
        return 'Paper Publications';
    }
  };

  return (
    <Container fluid className="dashboard-container">
      <h1 className="dashboard-title">MongoDB Paper Analysis</h1>
      
      {/* Filter Form */}
      <Card className="mb-4">
        <Card.Header>Filter Options</Card.Header>
        <Card.Body>
          <Form onSubmit={handleFilterSubmit}>
            <Row>
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Start Date</Form.Label>
                  <Form.Control 
                    type="date" 
                    value={startDate} 
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </Form.Group>
              </Col>
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>End Date</Form.Label>
                  <Form.Control 
                    type="date" 
                    value={endDate} 
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </Form.Group>
              </Col>
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Year Filter</Form.Label>
                  <Form.Control 
                    type="number" 
                    placeholder="e.g., 2023" 
                    value={yearFilter} 
                    onChange={(e) => setYearFilter(e.target.value)}
                  />
                </Form.Group>
              </Col>
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Category</Form.Label>
                  <Form.Select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    <option value="">All Categories</option>
                    {[...availableCategories].sort((a, b) => a.localeCompare(b)).map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>
            <div className="d-flex justify-content-end">
              <Button variant="secondary" className="me-2" onClick={clearFilters}>
                Clear Filters
              </Button>
              <Button variant="primary" type="submit">
                Apply Filters
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
      
      {/* View Selection Tabs */}
      <div className="view-tabs mb-4">
        <Button 
          variant={activeView === 'yearly' ? 'primary' : 'outline-primary'} 
          className="me-2" 
          onClick={() => setActiveView('yearly')}
        >
          Yearly View
        </Button>
        <Button 
          variant={activeView === 'monthly' ? 'primary' : 'outline-primary'} 
          className="me-2" 
          onClick={() => setActiveView('monthly')}
        >
          Monthly View
        </Button>
        <Button 
          variant={activeView === 'daily' ? 'primary' : 'outline-primary'} 
          onClick={() => setActiveView('daily')}
        >
          Daily View
        </Button>
      </div>
      
      {/* Paper Analysis Chart */}
      <Card className="mb-4">
        <Card.Header>{getChartLabel()}</Card.Header>
        <Card.Body>
          {loading ? (
            <div className="text-center p-5">
              <Spinner animation="border" />
              <p className="mt-3">Loading paper analysis data...</p>
            </div>
          ) : error ? (
            <div className="text-center p-5 text-danger">
              <p>{error}</p>
            </div>
          ) : (
            <>
              <div className="text-center mb-3">
                <h5>Total Papers: {paperAnalysis?.total_papers ? paperAnalysis.total_papers.toLocaleString() : 0}</h5>
              </div>
              <ResponsiveContainer width="100%" height={500}>
                {activeView === 'daily' ? (
                  <LineChart data={getChartData()} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="name" 
                      angle={-45} 
                      textAnchor="end" 
                      height={80} 
                      interval={0}
                      fontSize={12}
                    />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="papers" 
                      name="Paper Count" 
                      stroke="#8884d8" 
                      activeDot={{ r: 8 }} 
                    />
                  </LineChart>
                ) : (
                  <BarChart data={getChartData()} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="name" 
                      angle={-45} 
                      textAnchor="end" 
                      height={80} 
                      interval={0}
                      fontSize={12}
                    />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar 
                      dataKey="papers" 
                      name="Paper Count" 
                      fill="#8884d8" 
                    />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </>
          )}
        </Card.Body>
      </Card>
      
      {/* Tips and Information */}
      <Card>
        <Card.Header>Usage Tips</Card.Header>
        <Card.Body>
          <ul>
            <li>Use the filters to narrow down the publication date range</li>
            <li>Switch between yearly, monthly, and daily views for different granularity</li>
            <li>Hover over chart elements to see exact paper counts</li>
            <li>The yearly view is best for observing long-term trends</li>
            <li>The daily view shows publication patterns within shorter timeframes</li>
          </ul>
        </Card.Body>
      </Card>
    </Container>
  );
}

export default MongoDBReports;
